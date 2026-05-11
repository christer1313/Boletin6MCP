import argparse
import asyncio
import json
import os

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from mcp_config_langchain import build_nosql_server_config

# Agente NoSQL (LangChain) — usa MCP por Unix socket. Ver FLUJO_CONEXION_MCP.md


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
    config = build_nosql_server_config()
    client = MultiServerMCPClient(config)
    return await client.get_tools()


async def run_agent(prompt: str) -> str:
    """Ejecuta agente NoSQL con LLM usando herramientas MCP (async)."""
    tools = await _get_tools()
    agent = create_react_agent(build_model(), tools)
    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]
        }
    )
    messages = result.get("messages", [])
    if not messages:
        return str(result)
    return str(messages[-1].content)


async def run_direct_list_collections() -> str:
    """Lista colecciones de MongoDB directamente sin LLM (async)."""
    tools = await _get_tools()
    list_tool = next((tool for tool in tools if tool.name == "list_collections"), None)
    if list_tool is None:
        raise RuntimeError("No se encontro la herramienta MCP 'list_collections'.")
    return str(await list_tool.ainvoke({}))


async def run_direct_query(collection_name: str, query_filter_raw: str) -> str:
    """Ejecuta una query MongoDB directamente sin LLM (async)."""
    tools = await _get_tools()
    query_tool = next((tool for tool in tools if tool.name == "query_mongo"), None)
    if query_tool is None:
        raise RuntimeError("No se encontro la herramienta MCP 'query_mongo'.")

    try:
        query_filter = json.loads(query_filter_raw)
    except json.JSONDecodeError as exc:
        raise ValueError("El filtro debe ser JSON valido.") from exc

    payload = {
        "collection_name": collection_name,
        "query_filter": query_filter,
    }
    return str(await query_tool.ainvoke(payload))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Agente NoSQL con LangChain/LangGraph usando herramientas MCP"
    )
    parser.add_argument(
        "--prompt",
        default="Que colecciones hay en MongoDB?",
        help="Pregunta para el agente NoSQL.",
    )
    parser.add_argument(
        "--direct-list",
        action="store_true",
        help="Si se activa, lista colecciones directamente via MCP sin LLM.",
    )
    parser.add_argument(
        "--direct-collection",
        default="",
        help="Coleccion para consulta directa NoSQL.",
    )
    parser.add_argument(
        "--direct-filter",
        default="{}",
        help="Filtro JSON para consulta directa NoSQL.",
    )
    args = parser.parse_args()

    if args.direct_list:
        print(asyncio.run(run_direct_list_collections()))
    elif args.direct_collection:
        print(asyncio.run(run_direct_query(args.direct_collection, args.direct_filter)))
    else:
        print(asyncio.run(run_agent(args.prompt)))