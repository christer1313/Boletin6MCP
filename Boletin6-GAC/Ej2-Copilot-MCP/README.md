# Ejercicio 2: MCP Servers + GitHub Copilot

## Objetivo

Conectar los servidores MCP del Ejercicio 1 (SQL y NoSQL) a GitHub Copilot Chat en VS Code, para que el LLM use herramientas MCP al responder preguntas sobre bases de datos.

## Requisitos

- Docker y Docker Compose.
- VS Code con GitHub Copilot Chat.
- Servicios del Ejercicio 1 levantados.

## Paso 1: Levantar servidores MCP

```bash
cd Boletin6-GAC/Ej1-MCPServers
docker compose up -d
docker ps
```

## Paso 2: Configurar Copilot MCP en VS Code

En `settings.json` de VS Code, anade:

```json
{
  "github.copilot.chat.mcpServers": {
    "sql-server": {
      "command": "docker",
      "args": ["exec", "-i", "mcp_sql_service", "python", "/app/mcp_sql_server.py"]
    },
    "nosql-server": {
      "command": "docker",
      "args": ["exec", "-i", "mcp_nosql_service", "python", "/app/mcp_nosql_server.py"],
      "env": {
        "MONGO_URI": "mongodb://mongodb:27017/"
      }
    }
  }
}
```

Reinicia la ventana de VS Code (`Developer: Reload Window`) o el Codespace.

## Paso 3: Probar en Copilot Chat

Preguntas recomendadas:

- SQL: "Cuantos artistas hay en Chinook?"
- NoSQL: "Que colecciones hay en MongoDB?"

## Evidencia tecnica reproducible

```bash
cd Boletin6-GAC/Ej1-MCPServers

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

## Otros adjuntos

- Captura query al server SQL en Copilot Chat.
- Captura query al server NoSQL en Copilot Chat.