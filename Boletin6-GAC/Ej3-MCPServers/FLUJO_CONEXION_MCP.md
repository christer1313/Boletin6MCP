# Flujo de Conexión: Aplicaciones → Servidores MCP vía Unix Sockets

Este documento explica cómo se conectan **smolagents** y **LangChain/LangGraph** a los servidores MCP a través de Unix sockets persistentes.

---

## 📋 Vista General

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           HOST (máquina local)                          │
│                                                                         │
│  ┌────────────────────────┐                  ┌─────────────────────┐   │
│  │ Aplicación smolagents  │                  │ Aplicación LangChain│   │
│  │                        │                  │ /LangGraph          │   │
│  │ 1. MCPClient()         │                  │                     │   │
│  │ 2. SQL_SERVER_PARAMS   │                  │ 1. MultiServerMCP   │   │
│  │ 3. síncrono            │                  │    Client()         │   │
│  └────────┬───────────────┘                  │ 2. build_sql_      │   │
│           │                                  │    server_config()  │   │
│           │ (socat - UNIX-CONNECT)           │ 3. async/await      │   │
│           │                                  └────────┬────────────┘   │
│           │                                           │                │
│      /tmp/mcp-sockets/sql.sock ◄─────────────────────┘                │
│      /tmp/mcp-sockets/nosql.sock                                       │
│           │                                                            │
└───────────┼────────────────────────────────────────────────────────────┘
            │
            │ Unix Socket (comunicación bidireccional)
            │
┌───────────┼────────────────────────────────────────────────────────────┐
│           │              CONTENEDORES DOCKER (Ej1)                     │
│           │                                                            │
│           ▼                                                            │
│  /mcp-sockets/sql.sock  (compartido)                                  │
│           │                                                            │
│           ▼                                                            │
│  socat UNIX-LISTEN:/mcp-sockets/sql.sock,fork                        │
│  EXEC:mcp_sql_server.py                                              │
│           │                                                            │
│           ▼                                                            │
│  ┌─────────────────────┐                                              │
│  │ mcp_sql_server.py   │ ◄─ Servidor MCP real                         │
│  │ (long-running)      │                                              │
│  │                     │                                              │
│  │ - List tools        │                                              │
│  │ - execute_sql_query │                                              │
│  │ - etc.              │                                              │
│  └──────────┬──────────┘                                              │
│             │                                                         │
│             ▼                                                         │
│  ┌─────────────────────┐                                              │
│  │  Chinook.sqlite     │ ◄─ Base de datos SQL                        │
│  └─────────────────────┘                                              │
│                                                                        │
│  Igual para NoSQL (MongoDB):                                          │
│  /mcp-sockets/nosql.sock ──┬─→ socat ──→ mcp_nosql_server.py ──→ MongoDB
│                              │                                        │
│                            long-running                              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🔗 Conexión SMOLAGENTS (Síncrono)

### 1. Configuración en `mcp_config.py`

```python
from mcp import StdioServerParameters

SQL_SERVER_PARAMS = StdioServerParameters(
    command="socat",
    args=["-", "UNIX-CONNECT:/tmp/mcp-sockets/sql.sock"],
)
```

**¿Qué hace?**
- Define cómo conectar al socket Unix del servidor MCP
- `command="socat"`: usar herramienta socat
- `args=["-", "UNIX-CONNECT:/tmp/mcp-sockets/sql.sock"]`: 
  - `-` = usar stdin/stdout
  - `UNIX-CONNECT:/tmp/mcp-sockets/sql.sock` = conectar a este socket

### 2. Uso en `agent_sql_mcp.py`

```python
from smolagents import MCPClient, CodeAgent
from mcp_config import SQL_SERVER_PARAMS

# Abre conexión al socket
with MCPClient(SQL_SERVER_PARAMS, structured_output=False) as tools:
    # tools contiene: [execute_sql_query, ...]
    
    agent = CodeAgent(
        tools=tools,  # Herramientas del servidor MCP
        model=build_model(),
    )
    
    # Ejecuta el agente (síncrono)
    result = agent.run(prompt)
```

### 3. Flujo de ejecución paso a paso

```
1. MCPClient es inicializado con SQL_SERVER_PARAMS
                             ↓
2. Internamente MCPClient ejecuta:
   socat - UNIX-CONNECT:/tmp/mcp-sockets/sql.sock
                             ↓
3. socat se conecta al socket Unix
   (que está siendo escuchado por: socat UNIX-LISTEN:... EXEC:mcp_sql_server.py)
                             ↓
4. Se establece conexión bidireccional por stdio
   (host socat proceso) ←→ (docker socat proceso) ←→ (mcp_sql_server.py)
                             ↓
5. MCPClient.get_tools() obtiene lista de herramientas disponibles
   - execute_sql_query
   - (otras herramientas MCP)
                             ↓
6. CodeAgent usa estas herramientas para resolver el prompt
   - Razona qué tool usar
   - Ejecuta tool con argumentos
   - Recibe respuesta por stdio
   - Continúa hasta resolver
                             ↓
7. Retorna resultado
```

---

## 🔗 Conexión LANGCHAIN/LANGGRAPH (Asíncrono)

### 1. Configuración en `mcp_config_langchain.py`

```python
def build_sql_server_config() -> dict:
    return {
        "sql": {
            "command": "socat",
            "args": ["-", "UNIX-CONNECT:/tmp/mcp-sockets/sql.sock"],
            "transport": "stdio",
        }
    }
```

**¿Qué hace?**
- Define configuración para MultiServerMCPClient (LangChain)
- Mismo socat + socket Unix que smolagents
- Añade `transport: "stdio"` explícitamente

### 2. Uso en `agent_sql_langchain_mcp.py`

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from mcp_config_langchain import build_sql_server_config

# Función async para conectar
async def _get_tools():
    config = build_sql_server_config()
    
    # Crea cliente MultiServerMCP con la config
    client = MultiServerMCPClient(config)
    
    # Obtiene tools de forma async
    return await client.get_tools()

# En la función principal
async def run_agent(prompt: str) -> str:
    # Conecta al socket y obtiene tools
    tools = await _get_tools()
    
    # tools contiene: [execute_sql_query, ...]
    
    # Crea agente ReAct
    agent = create_react_agent(build_model(), tools)
    
    # Ejecuta de forma async (no bloquea)
    result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": prompt,
        }]
    })
    
    return result["messages"][-1].content
```

### 3. Flujo de ejecución paso a paso

```
1. MultiServerMCPClient es inicializado con config
   {"sql": {"command": "socat", "args": [...], "transport": "stdio"}}
                             ↓
2. Cuando se llama await client.get_tools():
   Internamente ejecuta (asyncio):
   socat - UNIX-CONNECT:/tmp/mcp-sockets/sql.sock
                             ↓
3. socat se conecta al socket Unix
   (que está siendo escuchado por: socat UNIX-LISTEN:... EXEC:mcp_sql_server.py)
                             ↓
4. Se establece conexión bidireccional por stdio (async)
   (host subprocess) ←→ (docker socat) ←→ (mcp_sql_server.py)
                             ↓
5. await client.get_tools() obtiene lista de herramientas
   - execute_sql_query
   - (otras herramientas MCP)
                             ↓
6. create_react_agent crea agente ReAct pattern
                             ↓
7. await agent.ainvoke(input) ejecuta el prompt de forma async
   - ReAct: piensa qué tool usar
   - Ejecuta tool (await tool.ainvoke())
   - Recibe respuesta
   - Continúa hasta resolver
   (Todo sin bloquear el event loop)
                             ↓
8. Retorna resultado
```

---

## 📊 Comparación: Smolagents vs LangChain

| Aspecto | Smolagents | LangChain/LangGraph |
|---------|-----------|-------------------|
| **Cliente MCP** | `MCPClient` | `MultiServerMCPClient` |
| **Configuración** | `StdioServerParameters` | `dict` |
| **Patrón** | Síncrono | Async/await |
| **Agente** | `CodeAgent` | `create_react_agent` (ReAct) |
| **Invocación** | `.run()` | `await .ainvoke()` |
| **Socket Unix** | ✅ socat | ✅ socat |
| **Conexión** | Persistente | Persistente (async) |
| **Overhead** | ~0ms (reutiliza) | ~0ms (reutiliza) |

---

## 🔍 Detalles técnicos: ¿Cómo funciona el socket Unix?

### En Docker (servidor, lado Ej1):

```yaml
mcp-sql:
  command:
    - socat
    - UNIX-LISTEN:/mcp-sockets/sql.sock,fork,mode=777
    - EXEC:mcp_sql_server.py
```

- `socat` actúa como **multiplexor**
- `UNIX-LISTEN:/mcp-sockets/sql.sock` = escucha en el socket
- `fork` = crea un nuevo proceso para cada conexión
- `EXEC:mcp_sql_server.py` = ejecuta el servidor MCP real
- `mode=777` = permisos para que el host pueda conectarse

### En Host (cliente, lado Ej3):

```python
SQL_SERVER_PARAMS = StdioServerParameters(
    command="socat",
    args=["-", "UNIX-CONNECT:/tmp/mcp-sockets/sql.sock"],
)
```

- `socat` actúa como **cliente**
- `-` = redirecciona stdin/stdout
- `UNIX-CONNECT:/tmp/mcp-sockets/sql.sock` = conecta al socket

### Flujo de datos (ejemplo):

```
Usuario en host                Docker                     Base de Datos
   │                             │                              │
   ├─ escribiré query ──────────→ socat (client) ─────────────→ socat (server)
   │                             │                              │
   │                             │                           ┌──────────────┐
   │                             │                      ┌────┤ mcp_sql_srv  │
   │                             │                      │    └──────────────┘
   │                             │                      │
   │                             │                      ├─► EXEC:mcp_sql_server.py
   │                             │                      │        │
   │                             │                      │        └─► Chinook.db
   │                             │                      │
   │ ←──────── resultado ←─────── socat ←──────────── mcp_sql_server.py
```

---

## ✅ Ventajas de la arquitectura Unix Sockets

1. **Persistencia**: Servidor corre una sola vez, se reutiliza
2. **Bajo overhead**: No reinicia procesos (~0ms)
3. **Local**: Sin TCP, sin acceso a red
4. **Bidireccional**: stdio permite comunicación ask-response
5. **Compatible**: Funciona con cualquier cliente MCP (socat, nc, etc)
6. **Escalable**: Con `fork`, múltiples conexiones concurrentes

---

## 🔧 Verificación de conectividad

Puedes verificar que todo funciona:

```bash
# Ver los sockets disponibles
ls -la /tmp/mcp-sockets/

# Probar conexión directa
echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}' | \
  socat - UNIX-CONNECT:/tmp/mcp-sockets/sql.sock

# Ejecutar un agente
python3 agent_sql_mcp.py --direct-query "SELECT COUNT(*) FROM Artist;"
```

---

## 📝 Resumen

- **Smolagents**: Usa `MCPClient` de forma síncrona
- **LangChain**: Usa `MultiServerMCPClient` de forma asíncrona
- **Ambas**: Se conectan al mismo Unix socket persistente vía `socat`
- **Servidor**: Corre en Docker, escucha en socket, multiplexa conexiones
- **Cliente**: Conecta al socket, intercambia JSON-RPC, obtiene herramientas
- **Beneficio**: Conexión rápida y persistente, sin reiniciar servidores
