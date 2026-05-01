from mcp.server.fastmcp import FastMCP
import sqlite3
import os

mcp = FastMCP("SQL-Chinook-Server")
# Ruta configurable para soportar ejecución local y contenedor Docker.
DB_PATH = os.getenv("DB_PATH", "/Chinook.sqlite")

@mcp.tool()
def get_database_schema() -> str:
    """
    Obtiene el esquema de la base de datos (tablas y columnas).
    Es esencial llamar a esto primero para saber qué consultar.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
    schema = "\n".join([row[0] for row in cursor.fetchall() if row[0]])
    conn.close()
    return schema

@mcp.tool()
def execute_sql_query(query: str) -> str:
    """
    Ejecuta cualquier instrucción SQL (SELECT, INSERT, UPDATE, DELETE).
    Devuelve los resultados o un mensaje de confirmación.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        if query.lower().strip().startswith(("update", "insert", "delete")):
            conn.commit()
            return f"Operación exitosa. Filas afectadas: {cursor.rowcount}"
        
        results = cursor.fetchall()
        return str(results)
    except Exception as e:
        return f"Error ejecutando SQL: {e}"
    finally:
        conn.close()

@mcp.prompt()
def analizar_ventas(year: str) -> str:
    """
    Capa de abstracción para reportes de ventas anuales.
    Explica al LLM cómo usar las herramientas internas para dar un resultado de negocio.
    """
    return f"""
    Actúa como analista de datos. El usuario quiere un informe de ventas del año {year}.
    1. Usa 'get_database_schema' para confirmar la estructura de la tabla 'Invoice'.
    2. Ejecuta una query para contar facturas y sumar el campo 'Total' del año {year}.
    3. Devuelve un resumen amigable, no la tabla cruda.
    """

if __name__ == "__main__":
    print("[mcp_sql] Iniciando SQL MCP server...")
    try:
        mcp.run()
    except Exception as e:
        import traceback
        print("[mcp_sql] Excepción en mcp.run():", e)
        traceback.print_exc()
        raise
    # Mantener el proceso vivo para permitir depuración y conexiones externas
    import time
    while True:
        time.sleep(3600)
