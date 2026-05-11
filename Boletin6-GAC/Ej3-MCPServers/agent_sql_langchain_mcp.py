import argparse
import asyncio
import os

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from mcp_config_langchain import build_sql_server_config

# Agente SQL (LangChain) — usa MCP por Unix socket. Ver FLUJO_CONEXION_MCP.md


def build_model() -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("Define OPENAI_API_KEY para ejecutar el agente con LLM.")

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL")

    model_kwargs: dict[str, object] = {
        "model": model_name,
        "temperature": 0,
        "api_key": api_key,
    }
    if base_url:
        model_kwargs["base_url"] = base_url

    return ChatOpenAI(**model_kwargs)


async def _get_tools():
    """Conecta al servidor MCP y obtiene herramientas de forma asíncrona."""
    config = build_sql_server_config()
    client = MultiServerMCPClient(config)
    return await client.get_tools()


async def run_agent(prompt: str) -> str:
    """Ejecuta agente SQL con LLM usando herramientas MCP (async)."""
    tools = await _get_tools()
    system_hint = (
        "Usa herramientas MCP con argumentos nombrados. "
        "Para SQL utiliza execute_sql_query con query='...'."
    )
    agent = create_react_agent(build_model(), tools)
    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"{system_hint}\n\nPregunta del usuario: {prompt}",
                }
            ]
        }
    )
    messages = result.get("messages", [])
    if not messages:
        return str(result)
    return str(messages[-1].content)


async def run_direct_sql(query: str) -> str:
    """Ejecuta una query SQL directamente sin LLM (async)."""
    tools = await _get_tools()
    sql_tool = next((tool for tool in tools if tool.name == "execute_sql_query"), None)
    if sql_tool is None:
        raise RuntimeError("No se encontro la herramienta MCP 'execute_sql_query'.")
    return str(await sql_tool.ainvoke({"query": query}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Agente SQL con LangChain/LangGraph usando herramientas MCP"
    )
    parser.add_argument(
        "--prompt",
        default="Cuantos artistas hay en Chinook?",
        help="Pregunta para el agente SQL.",
    )
    parser.add_argument(
        "--direct-query",
        default="",
        help="Si se indica, ejecuta esta query SQL directamente via MCP sin LLM.",
    )
    args = parser.parse_args()

    if args.direct_query:
        print(asyncio.run(run_direct_sql(args.direct_query)))
    else:
        print(asyncio.run(run_agent(args.prompt)))
    parser.add_argument(
        "--prompt",
        default="Cuantos artistas hay en Chinook?",
        help="Pregunta para el agente SQL.",
    )
    parser.add_argument(
        "--direct-query",
        default="",
        help="Si se indica, ejecuta esta query SQL directamente via MCP sin LLM.",
    )
    args = parser.parse_args()

    if args.direct_query:
        print(asyncio.run(run_direct_sql(args.direct_query)))
    else:
        print(asyncio.run(run_agent(args.prompt)))