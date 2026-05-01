# Ejercicio 1: MCP server para bases de datos

## Objetivo

Desarrollar dos servidores MCP separados:

- Un servidor orientado a base de datos SQL (SQLite - Chinook).
- Un servidor orientado a base de datos NoSQL (MongoDB).

Ambos servidores exponen herramientas para consulta de datos, tal y como se trabajó en boletines anteriores.
De forma opcional, tambien se expone un prompt en el servidor SQL.
La ejecucion se realiza en contenedores Docker mediante `docker compose`.

## Estructura del ejercicio

```text
Boletin6-GAC/Ej1-MCPServers/
├── docker-compose.yml
├── mcp-sql/
│   ├── Dockerfile
│   ├── mcp_sql_server.py
│   └── requirements.txt
└── mcp-nosql/
    ├── Dockerfile
    ├── mcp_nosql_server.py
    ├── seed.py
    └── requirements.txt
```

## Servidor MCP SQL

Archivo: `mcp-sql/mcp_sql_server.py`

Base de datos usada:

- SQLite Chinook montada en el contenedor como `/Chinook.sqlite`.

Herramientas expuestas:

- `get_database_schema()`
- `execute_sql_query(query: str)`

Prompt opcional expuesto:

- `analizar_ventas(year: str)`

## Servidor MCP NoSQL

Archivo: `mcp-nosql/mcp_nosql_server.py`

Base de datos usada:

- MongoDB (`mongodb://mongodb:27017/`), base `tienda_musica`.

Herramientas expuestas:

- `list_collections()`
- `query_mongo(collection_name: str, query_filter: dict)`

Seed de datos:

- `mcp-nosql/seed.py`

## Ejecutar

```bash
cd Boletin6-GAC/Ej1-MCPServers
docker compose up -d
docker compose ps
```

## Parar

```bash
cd Boletin6-GAC/Ej1-MCPServers
docker compose down
```

## Pruebas rapidas

```bash
# SQL MCP
docker exec -i mcp_sql_service python -c "from mcp_sql_server import execute_sql_query; print(execute_sql_query(\"SELECT COUNT(*) FROM Artist;\"))"

# NoSQL MCP
docker exec -i mcp_nosql_service python -c "from mcp_nosql_server import list_collections; print(list_collections())"
```

Salida esperada (ejemplo):

```text
[(275,)]
['productos']
```

Si SQL devuelve `unable to open database file`:

```bash
docker compose build mcp-sql
docker compose up -d --force-recreate mcp-sql
```
