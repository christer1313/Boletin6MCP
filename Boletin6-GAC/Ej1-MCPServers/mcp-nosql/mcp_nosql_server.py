from mcp.server.fastmcp import FastMCP
from pymongo import MongoClient
import os

# Nombre del servidor MCP
mcp = FastMCP("NoSQL-Mongo-Server")

# Conexión a MongoDB (usaremos el nombre del servicio en Docker Compose)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
client = MongoClient(MONGO_URI)
db = client['tienda_musica']

@mcp.tool()
def list_collections() -> list:
    """Lista todas las colecciones disponibles en la base de datos NoSQL."""
    return db.list_collection_names()

@mcp.tool()
def query_mongo(collection_name: str, query_filter: dict) -> str:
    """
    Consulta documentos en una colección de MongoDB.
    Ejemplo de filtro: {"categoria": "Instrumentos"}
    """
    try:
        results = list(db[collection_name].find(query_filter).limit(10))
        for res in results:
            res['_id'] = str(res['_id'])
        return str(results)
    except Exception as e:
        return f"Error en Mongo: {str(e)}"

if __name__ == "__main__":
    print("[mcp_nosql] Iniciando NoSQL MCP server...")
    try:
        mcp.run()
    except Exception as e:
        import traceback
        print("[mcp_nosql] Excepción en mcp.run():", e)
        traceback.print_exc()
        raise
    # Mantener el proceso vivo para permitir depuración y conexiones externas
    import time
    while True:
        time.sleep(3600)
