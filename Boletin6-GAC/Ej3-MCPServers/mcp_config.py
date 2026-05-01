from mcp import StdioServerParameters


# Punto central de integracion MCP para smolagents.
#
# Cada entrada `StdioServerParameters` define como lanzar un servidor MCP por
# stdio. En este caso, smolagents ejecuta `docker exec` dentro de contenedores
# ya activos del Ejercicio 1.
#
# Ventaja: los agentes no implementan herramientas locales; reutilizan
# directamente las herramientas publicadas por los MCP servers.

SQL_SERVER_PARAMS = StdioServerParameters(
    command="docker",
    args=["exec", "-i", "mcp_sql_service", "python", "/app/mcp_sql_server.py"],
)

NOSQL_SERVER_PARAMS = StdioServerParameters(
    command="docker",
    args=["exec", "-i", "mcp_nosql_service", "python", "/app/mcp_nosql_server.py"],
)


def get_all_server_params() -> list[StdioServerParameters]:
    """Devuelve ambos servidores para escenarios multi-MCP."""
    return [SQL_SERVER_PARAMS, NOSQL_SERVER_PARAMS]
