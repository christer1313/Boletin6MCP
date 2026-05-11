# Ejercicio 3: Agentes MCP con smolagents y LangChain

## Objetivo

Conectar agentes a los servidores MCP ya desplegados en Docker usando sockets Unix persistentes y ejecutar el flujo completo con LLMs.

La entrega queda dividida en dos partes:
- **smolagents**: dos pruebas individuales, una para SQL y otra para NoSQL.
- **LangChain**: un único script con orquestador que resuelve la consulta completa según el tipo de pregunta.

## Idea de diseño

En este ejercicio usamos un único modelo por framework para no añadir complejidad innecesaria:
- smolagents usa Hugging Face con `HF_TOKEN`.
- LangChain usa Ollama Cloud con `OLLAMA_API_KEY`.

La selección del flujo es simple:
- Si quieres probar SQL, ejecutas el agente SQL.
- Si quieres probar NoSQL, ejecutas el agente NoSQL.
- Si quieres resolver una consulta completa con LangChain, ejecutas el orquestador.

## Archivos principales

- `mcp_config_smolagents.py`: configuración MCP para smolagents.
- `mcp_config_langchain.py`: configuración MCP para LangChain.
- `agent_sql_smolagents.py`: agente SQL con smolagents.
- `agent_nosql_smolagents.py`: agente NoSQL con smolagents.
- `agent_sql_langchain.py`: agente SQL con LangChain.
- `agent_nosql_langchain.py`: agente NoSQL con LangChain.
- `orchestrator_langchain.py`: orquestador LangChain que decide y resuelve la consulta completa.
- `requirements.txt`: dependencias del ejercicio.
- `FLUJO_CONEXION_MCP.md`: explicación detallada de la conexión por sockets Unix.
- `ARQUITECTURA_ORQUESTADOR.md`: explicación de la parte de orquestación.

## Flujo de ejecución correcto

### 1. Arrancar los servidores MCP en Ej1

Primero levanta los contenedores del ejercicio anterior:

```bash
cd ../Ej1-MCPServers
docker compose build
docker compose up -d
docker compose ps
```

Debes ver activos `mcp_sql_service`, `mcp_nosql_service` y `mongodb`.

### 2. Verificar que existen los sockets

```bash
ls -la /tmp/mcp-sockets/
```

Deberías ver:
- `sql.sock`
- `nosql.sock`

### 3. Instalar dependencias del Ej3

```bash
cd ../Ej3-MCPServers
python3 -m pip install -r requirements.txt
```

### 4. Definir credenciales del modelo

Opción A: **Usando `.env`** (Recomendado)

Edita el archivo `.env` y reemplaza los placeholders con tus credenciales:

```bash
# Edita .env
HF_TOKEN=tu_token_huggingface_aqui
OLLAMA_API_KEY=tu_ollama_cloud_token_aqui
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_MODEL=gpt-oss:120b-cloud
```

Los scripts cargarán automáticamente las variables del `.env`.

Opción B: **Usando variables de entorno**

#### smolagents

Usa Hugging Face con `HF_TOKEN`:

```bash
export HF_TOKEN="tu_token_huggingface"
```

#### LangChain

Usa Ollama Cloud con `OLLAMA_API_KEY`:

```bash
export OLLAMA_API_KEY="tu_api_key_ollama"
export OLLAMA_MODEL="gpt-oss:120b-cloud"
export OLLAMA_BASE_URL="https://ollama.com"
```

## Flujo de entrega

### Parte 1: smolagents

Aquí se hacen dos pruebas independientes:

#### SQL

```bash
python3 agent_sql_smolagents.py --prompt "Cuantos artistas hay en Chinook?"
```

**Resultado esperado:**
```
275
```

#### NoSQL

```bash
python3 agent_nosql_smolagents.py --prompt "Que colecciones hay en MongoDB?"
```

**Resultado esperado:**
```
Las colecciones disponibles en MongoDB son: productos
```

### Parte 2: LangChain con orquestador

En esta parte, el flujo completo lo resuelve el script del orquestador.

#### Consulta SQL

```bash
python3 orchestrator_langchain.py --query "Cuantos artistas hay en Chinook?"
```

**Resultado esperado:**
```
[(275,)]
```

#### Consulta NoSQL

```bash
python3 orchestrator_langchain.py --query "Que colecciones hay en MongoDB?"
```

**Resultado esperado:**
```
productos
```

#### Consulta SQL con LLM

```bash
python3 orchestrator_langchain.py --query "Cual es el género más popular en la tabla Genre?"
```

**Resultado esperado:**
```
[('Rock', 1297)]
```

## Flujo de conexión MCP

Los agentes no hablan con la base de datos directamente. El flujo real es:

1. Docker levanta los servidores MCP.
2. Cada servidor expone un socket Unix en `/tmp/mcp-sockets/`.
3. El agente local se conecta a ese socket con `socat`.
4. El cliente MCP obtiene las herramientas disponibles.
5. El agente ejecuta la herramienta correspondiente.

Esquema simplificado:

```text
Agente local -> socat -> /tmp/mcp-sockets/sql.sock -> servidor MCP -> base de datos
```

Para el detalle completo del flujo, ver [FLUJO_CONEXION_MCP.md](FLUJO_CONEXION_MCP.md).

## Troubleshooting

### No aparece `sql.sock` o `nosql.sock`

Si el directorio existe pero no aparecen los sockets, revisa que los contenedores MCP estén en ejecución:

```bash
cd ../Ej1-MCPServers
docker compose ps
```

Si no están arriba:

```bash
docker compose build
docker compose up -d
```

### Error de credenciales

#### smolagents

```text
Define HF_TOKEN para ejecutar el agente con LLM.
```

#### LangChain

```text
Define OLLAMA_API_KEY para ejecutar LangChain con Ollama.
```

### Error de conexión al socket

Si sale un error tipo `No such file or directory`, normalmente significa que el contenedor MCP no llegó a crear el socket. En ese caso:

```bash
cd ../Ej1-MCPServers
docker compose down -v
docker compose build
docker compose up -d
```

## Resumen

- smolagents usa `HF_TOKEN` (cargado desde `.env` o variable de entorno).
- smolagents se presenta con dos pruebas individuales: SQL y NoSQL.
- LangChain usa `OLLAMA_API_KEY` (cargado desde `.env` o variable de entorno).
- LangChain resuelve la consulta completa desde `orchestrator_langchain.py`.
- El router automático detecta si usar SQL, NoSQL o ambos.
- La traducción de preguntas naturales a SQL se hace con LLM.
- La conexión a MCP se hace por sockets Unix persistentes.
- Las credenciales se cargan automáticamente desde `.env` con `python-dotenv`.
