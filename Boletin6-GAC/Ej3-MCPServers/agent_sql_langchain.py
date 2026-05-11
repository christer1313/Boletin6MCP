import argparse
import os

from dotenv import load_dotenv

load_dotenv()

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama

from mcp_config_langchain import build_sql_server_config

# Agente SQL (LangChain) — especializado en queries SQL. Ver FLUJO_CONEXION_MCP.md


def build_model() -> ChatOllama:
    ollama_api_key = os.getenv("OLLAMA_API_KEY")
    if not ollama_api_key:
        raise EnvironmentError("Define OLLAMA_API_KEY para ejecutar el agente con LLM.")

    model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")
    base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")

    return ChatOllama(
        model=model_name,
        base_url=base_url,
        headers={"Authorization": f"Bearer {ollama_api_key}"},
        temperature=0,
    )


async def get_tools():
    """Obtiene solo las herramientas SQL."""
    config = build_sql_server_config()
    client = MultiServerMCPClient(config)
    return await client.get_tools()


async def execute_sql_query(query: str) -> str:
    """Ejecuta una query SQL usando la herramienta MCP."""
    tools = await get_tools()
    sql_tool = next((tool for tool in tools if tool.name == "execute_sql_query"), None)
    if sql_tool is None:
        raise RuntimeError("No se encontro la herramienta MCP 'execute_sql_query'.")
    result = await sql_tool.ainvoke({"query": query})
    
    # Si el resultado es una lista de dicts (típico de herramientas MCP),extrae el 'text'
    if isinstance(result, list) and len(result) > 0:
        if isinstance(result[0], dict) and 'text' in result[0]:
            return result[0]['text']
    
    return str(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente SQL (LangChain)")
    parser.add_argument("--query", help="Query SQL a ejecutar")
    args = parser.parse_args()

    if args.query:
        import asyncio
        print(asyncio.run(execute_sql_query(args.query)))
