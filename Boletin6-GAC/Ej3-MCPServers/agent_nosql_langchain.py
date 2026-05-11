import argparse
import asyncio
import json
import os

from dotenv import load_dotenv

load_dotenv()

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama

from mcp_config_langchain import build_nosql_server_config

# Agente NoSQL (LangChain) — especializado en queries MongoDB. Ver FLUJO_CONEXION_MCP.md


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
    """Obtiene solo las herramientas NoSQL."""
    config = build_nosql_server_config()
    client = MultiServerMCPClient(config)
    return await client.get_tools()


async def list_collections() -> str:
    """Lista todas las colecciones MongoDB."""
    tools = await get_tools()
    list_tool = next((tool for tool in tools if tool.name == "list_collections"), None)
    if list_tool is None:
        raise RuntimeError("No se encontro la herramienta MCP 'list_collections'.")
    return str(await list_tool.ainvoke({}))


async def query_mongo(collection_name: str, query_filter: dict) -> str:
    """Ejecuta una query MongoDB."""
    tools = await get_tools()
    query_tool = next((tool for tool in tools if tool.name == "query_mongo"), None)
    if query_tool is None:
        raise RuntimeError("No se encontro la herramienta MCP 'query_mongo'.")

    payload = {
        "collection_name": collection_name,
        "query_filter": query_filter,
    }
    return str(await query_tool.ainvoke(payload))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente NoSQL (LangChain)")
    parser.add_argument("--list", action="store_true", help="Listar colecciones")
    parser.add_argument("--collection", help="Colección a consultar")
    parser.add_argument("--filter", help="Filtro JSON")
    args = parser.parse_args()

    if args.list:
        print(asyncio.run(list_collections()))
    elif args.collection and args.filter:
        query_filter = json.loads(args.filter)
        print(asyncio.run(query_mongo(args.collection, query_filter)))
