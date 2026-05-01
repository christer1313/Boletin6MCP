# Ejercicio 3: smolagents + MCP client

## Objetivo

Adaptar los agentes del boletin anterior para que usen herramientas remotas de los servidores MCP ya creados:

- SQL MCP (`mcp_sql_service`)
- NoSQL MCP (`mcp_nosql_service`)

En este ejercicio, `smolagents` consume herramientas MCP mediante `MCPClient`.

## Archivos

- `mcp_config.py`: configuracion MCP compartida por todos los agentes.
- `agent_sql_mcp.py`: agente SQL usando herramientas MCP.
- `agent_nosql_mcp.py`: agente NoSQL usando herramientas MCP.
- `requirements.txt`: dependencias necesarias.

## Por que `mcp_config.py` es clave

`mcp_config.py` es la pieza que incorpora MCP a `smolagents`.

- Define dos `StdioServerParameters` (SQL y NoSQL).
- Indica a `MCPClient` como arrancar cada servidor MCP con `docker exec`.
- Centraliza la configuracion para evitar duplicarla en cada agente.
- Permite cambiar comando, args o contenedor en un solo sitio.

Flujo resumido:

1. El agente crea `MCPClient(SQL_SERVER_PARAMS)` o `MCPClient(NOSQL_SERVER_PARAMS)`.
2. `MCPClient` conecta por stdio al servidor MCP remoto.
3. `get_tools()` devuelve herramientas MCP listas para `CodeAgent`.
4. El agente ejecuta esas herramientas como si fueran tools locales.

## Requisitos

1. Levantar contenedores del Ejercicio 1:

```bash
cd ../Ej1-MCPServers
docker compose up -d
```

2. Instalar dependencias en esta carpeta:

```bash
cd ../Ej3-MCPServers
python3 -m pip install -r requirements.txt
```

3. (Opcional, para agentes con LLM) definir token HF:

```bash
export HF_TOKEN="tu_token"
```

## Pruebas rapidas (sin LLM)

Puedes validar cada agente con invocacion directa de herramienta MCP:

```bash
# SQL directo
python3 agent_sql_mcp.py --direct-query "SELECT COUNT(*) FROM Artist;"

# NoSQL directo
python3 agent_nosql_mcp.py --direct-list
```

## Ejecutar agentes adaptados

### SQL

```bash
python3 agent_sql_mcp.py --direct-query "SELECT COUNT(*) FROM Artist;"
python3 agent_sql_mcp.py --prompt "Cuantos artistas hay en Chinook?"
```

### NoSQL

```bash
python3 agent_nosql_mcp.py --direct-list
python3 agent_nosql_mcp.py --prompt "Que colecciones hay en MongoDB?"
```

## Notas

- Las opciones `--direct-*` no requieren `HF_TOKEN` porque invocan la herramienta MCP de forma directa.
- Las opciones `--prompt` si requieren `HF_TOKEN` porque ejecutan el agente con modelo LLM.
- Si falla la conexion, verifica que `mcp_sql_service` y `mcp_nosql_service` esten en estado `Up`.
