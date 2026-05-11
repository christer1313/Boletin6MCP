"""Configuración MCP para LangChain/LangGraph: conecta a servidores MCP por Unix sockets.

Los servidores ya están corriendo en Docker (Ej1) y escuchando en estos sockets.
Ver FLUJO_CONEXION_MCP.md para detalles técnicos de la conexión.
"""

from __future__ import annotations


def build_sql_server_config() -> dict[str, dict[str, object]]:
    """Configuración del servidor SQL MCP para LangChain."""
    return {
        "sql": {
            "command": "socat",
            "args": ["-", "UNIX-CONNECT:/tmp/mcp-sockets/sql.sock"],
            "transport": "stdio",
        }
    }


def build_nosql_server_config() -> dict[str, dict[str, object]]:
    """Configuración del servidor NoSQL MCP para LangChain."""
    return {
        "nosql": {
            "command": "socat",
            "args": ["-", "UNIX-CONNECT:/tmp/mcp-sockets/nosql.sock"],
            "transport": "stdio",
        }
    }


def build_all_servers_config() -> dict[str, dict[str, object]]:
    config = {}
    config.update(build_sql_server_config())
    config.update(build_nosql_server_config())
    return config