from mcp import StdioServerParameters

# Configuración MCP para smolagents: se conecta a servidores MCP por Unix sockets
# Los servidores ya están corriendo en Docker (Ej1) y escuchando en estos sockets
# Ver FLUJO_CONEXION_MCP.md para detalles técnicos de la conexión

SQL_SERVER_PARAMS = StdioServerParameters(
    command="socat",
    args=["-", "UNIX-CONNECT:/tmp/mcp-sockets/sql.sock"],
)

NOSQL_SERVER_PARAMS = StdioServerParameters(
    command="socat",
    args=["-", "UNIX-CONNECT:/tmp/mcp-sockets/nosql.sock"],
)


def get_all_server_params() -> list[StdioServerParameters]:
    """Devuelve ambos servidores para escenarios multi-MCP."""
    return [SQL_SERVER_PARAMS, NOSQL_SERVER_PARAMS]
