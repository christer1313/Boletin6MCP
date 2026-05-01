# mcp-nosql/seed.py
from pymongo import MongoClient
import os
import time

# Esperar un poco a que Mongo arranque realmente
time.sleep(5)

client = MongoClient(os.getenv("MONGO_URI", "mongodb://mongodb:27017/"))
db = client['tienda_musica']

if "productos" not in db.list_collection_names():
    db.productos.insert_many([
        {"nombre": "Guitarra Gibson", "precio": 1200, "categoria": "Instrumentos", "stock": 3},
        {"nombre": "Bajo Fender", "precio": 900, "categoria": "Instrumentos", "stock": 5},
        {"nombre": "Púas Pack x10", "precio": 5, "categoria": "Accesorios", "stock": 100}
    ])
    print("🌱 Datos de prueba insertados en MongoDB.")
else:
    print("✅ La base de datos ya tiene datos.")