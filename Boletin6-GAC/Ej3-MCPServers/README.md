# Ejercicio 3: Agentes con cliente MCP (smolagents y LangChain/LangGraph)

## Objetivo

Adaptar los agentes del boletin anterior para que usen herramientas remotas de los servidores MCP ya creados:

- SQL MCP (`mcp_sql_service`)
- NoSQL MCP (`mcp_nosql_service`)

En este ejercicio, tanto `smolagents` como `LangChain/LangGraph` consumen herramientas MCP a través de **Unix sockets persistentes**, evitando la sobrecarga de reiniciar procesos en cada llamada.

## Archivos

- `mcp_config.py`: configuración MCP para smolagents usando Unix sockets.
- `mcp_config_langchain.py`: configuración MCP para LangChain/LangGraph usando Unix sockets.
- `agent_sql_smolagents.py`: agente SQL con smolagents usando herramientas MCP.
- `agent_nosql_smolagents.py`: agente NoSQL con smolagents usando herramientas MCP.
- `agent_sql_langchain_mcp.py`: agente SQL con LangChain/LangGraph usando herramientas MCP.
- `agent_nosql_langchain_mcp.py`: agente NoSQL con LangChain/LangGraph usando herramientas MCP.
- `requirements.txt`: dependencias necesarias.
- **`FLUJO_CONEXION_MCP.md`**: Documentación detallada del flujo de conexión (ver para profundizar).

## Flujo de Conexión (Resumen)

```
Servidor MCP (Docker)              Cliente (Host)
────────────────────────────────   ──────────────────

socat UNIX-LISTEN:…                MCPClient / MultiServerMCPClient
EXEC:mcp_sql_server.py  ◄──────────► socat UNIX-CONNECT:…
                                    (smolagents / LangChain)

Conexión persistente por Unix socket → sin reiniciar servidor
```

**Para detalles técnicos completos, ver `FLUJO_CONEXION_MCP.md`**

## Requisitos previos

### 1. Docker Compose (Ej1) corriendo en background

Primero, asegúrate de tener los contenedores del Ej1 levantados:

```bash
cd ../Ej1-MCPServers

# Reconstruir con la nueva configuración (socat en Dockerfiles)
docker compose build

# Levantar en background
docker compose up -d

# Verificar que estén corriendo
docker compose ps
# Esperado: mcp_sql_service, mcp_nosql_service, mongodb, mongo_seeding en estado "Up"
```

### 2. Instalar `socat` en el host

`socat` es la herramienta que permite conectarse a los Unix sockets desde el host.

**En Linux (Debian/Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install -y socat
```

**Verificar instalación:**
```bash
socat -V
```

### 3. Instalar dependencias Python en Ej3

```bash
cd ../Ej3-MCPServers
python3 -m pip install -r requirements.txt
```

### 4. Definir credenciales de LLM (opcional, solo si usas agentes con LLM)

```bash
# Para smolagents
export HF_TOKEN="tu_token_huggingface"

# Para LangChain/LangGraph
export OPENAI_API_KEY="tu_api_key_openai"
export OPENAI_MODEL="gpt-4o-mini"              # Opcional
export OPENAI_BASE_URL="https://api.openai.com/v1"  # Opcional
```

## Verificación de conectividad

Antes de ejecutar agentes, verifica que los sockets están siendo escuchados:

```bash
# Ver los sockets disponibles
ls -la /tmp/mcp-sockets/

# Esperado:
# sql.sock (Unix socket)
# nosql.sock (Unix socket)

# Probar conexión directa (debe responder sin error)
echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}' | \
  socat - UNIX-CONNECT:/tmp/mcp-sockets/sql.sock | head -1

# Esperado: respuesta JSON válida
```

## Pruebas rápidas (sin LLM)

Puedes validar cada agente con invocación directa de herramienta MCP **sin credenciales de LLM**:

### Smolagents

```bash
# SQL directo
python3 agent_sql_smolagents.py --direct-query "SELECT COUNT(*) FROM Artist;"

# NoSQL directo
python3 agent_nosql_smolagents.py --direct-list
```

### LangChain/LangGraph

```bash
# SQL directo
python3 agent_sql_langchain_mcp.py --direct-query "SELECT COUNT(*) FROM Artist;"

# NoSQL directo
python3 agent_nosql_langchain_mcp.py --direct-list
```

## Ejecutar agentes con LLM (requiere credenciales)

### Smolagents

#### SQL con agente

```bash
export HF_TOKEN="tu_token"
python3 agent_sql_smolagents.py --prompt "Cuantos artistas hay en Chinook?"
```

#### NoSQL con agente

```bash
export HF_TOKEN="tu_token"
python3 agent_nosql_smolagents.py --prompt "Que colecciones hay en MongoDB?"
```

### LangChain/LangGraph

#### SQL con agente

```bash
export OPENAI_API_KEY="tu_api_key"
python3 agent_sql_langchain_mcp.py --prompt "Cuantos artistas hay en Chinook?"
```

#### NoSQL con agente

```bash
export OPENAI_API_KEY="tu_api_key"
python3 agent_nosql_langchain_mcp.py --prompt "Que colecciones hay y cuantos documentos tienen?"
```

## ¿Cómo funciona?

### Por qué Unix Sockets

El despliegue usa **Unix sockets** en lugar de ejecutar `docker exec` cada vez:

| Aspecto | Approach Anterior | Actual (Sockets) |
|--------|------------------|-----------------|
| **Servidor** | Se reinicia en cada llamada | Corre continuamente |
| **Overhead** | ~500ms+ (reinicio) | ~0ms (reutiliza) |
| **Comunicación** | CLI subprocess | stdio bidireccional |
| **Eficiencia** | Baja | Alta ✅ |

### Arquitectura

```
Docker Container (long-running)                  Host
─────────────────────────────────────────────    ────────

mcp_sql_server.py                                 MCPClient (smolagents)
        ↑                                               ↑
    stdio loop                                    stdio connection
        ↑                                               ↑
socat UNIX-LISTEN                                  socat UNIX-CONNECT
    ↓                                                   ↓
/mcp-sockets/sql.sock ◄─────────────────────────► /tmp/mcp-sockets/sql.sock

→ Conexión persistente, sin reiniciar
```

Para detalles técnicos, diagrama completo, y explicación paso a paso, ver **`FLUJO_CONEXION_MCP.md`**.

## Troubleshooting

### Error: "Permission denied" al conectar a socket

```
FileNotFoundError: [Errno 13] Permission denied: '/tmp/mcp-sockets/sql.sock'
```

**Solución:**
```bash
# Verificar permisos del socket
ls -la /tmp/mcp-sockets/sql.sock

# Deben tener permisos 777 o al menos para tu usuario
# Si no, reconstruir docker-compose:
cd ../Ej1-MCPServers
docker compose down -v
docker compose build
docker compose up -d
```

### Error: "Connection refused" al conectar a socket

```
errno 111: Connection refused
```

**Solución:**
```bash
# Verificar que los contenedores están corriendo
docker compose -f ../Ej1-MCPServers/docker-compose.yml ps

# Si no están UP, levantarlos:
cd ../Ej1-MCPServers
docker compose up -d

# Esperar a que estén listos (suele tardar ~5-10 segundos)
sleep 5

# Verificar socket nuevamente
ls -la /tmp/mcp-sockets/
```

### Error: "socat: command not found"

```
FileNotFoundError: [Errno 2] No such file or directory: 'socat'
```

**Solución:**
```bash
# Instalar socat en el host
sudo apt-get install -y socat

# Verificar
socat -V
```

### Error: LLM credentials not provided (smolagents)

```
EnvironmentError: Define HF_TOKEN para ejecutar el agente con LLM.
```

**Solución:**
```bash
export HF_TOKEN="tu_token_valido"
python3 agent_sql_smolagents.py --prompt "..."
```

Para obtener token: https://huggingface.co/settings/tokens

### Error: LLM credentials not provided (LangChain)

```
EnvironmentError: Define OPENAI_API_KEY para ejecutar el agente con LLM.
```

**Solución:**
```bash
export OPENAI_API_KEY="tu_api_key_valida"
python3 agent_sql_langchain_mcp.py --prompt "..."
```

Para obtener API key: https://platform.openai.com/api-keys

## Notas importantes

- **Las opciones `--direct-*`** no requieren credenciales de LLM. Invocan la herramienta MCP directamente.
- **Las opciones `--prompt`** sí requieren credenciales del proveedor LLM.
- **Los contenedores deben estar corriendo** antes de ejecutar cualquier agente.
- **Los sockets persisten** mientras Docker Compose esté activo. Para limpiar:
  ```bash
  cd ../Ej1-MCPServers
  docker compose down -v
  ```
- **La comunicación es local (Unix sockets)**, no requiere TCP, HTTP ni acceso a red.

## Arquitectura: Unix Sockets (Persistente)

```
┌─────────────────────────────────────────────────────────────────┐
│ Host (Cliente MCP - smolagents / LangChain)                     │
│                                                                 │
│  mcp_config.py:                                                 │
│  command="socat"                                                │
│  args=["-", "UNIX-CONNECT:/tmp/mcp-sockets/sql.sock"]          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                   stdio (persistente)
                             │
                             ▼
                    /tmp/mcp-sockets/sql.sock
                    (Unix domain socket)
                             │
                   stdio (persistente)
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ Contenedor Docker (Servidor MCP - long-running)               │
│                                                                │
│  docker-compose.yml:                                           │
│  command: ["socat", "UNIX-LISTEN:/mcp-sockets/sql.sock",      │
│            "EXEC:mcp_sql_server.py"]                          │
│                                                                │
│  Status: UP (siempre corriendo)                              │
└────────────────────────────────────────────────────────────────┘
```

### Ventajas sobre `docker exec`

| Aspecto | docker exec | Unix Sockets |
|--------|-------------|--------------|
| **Servidor** | Inicia cada vez | Corre continuamente ✅ |
| **Startup** | ~500ms+ | ~0ms (reutiliza conexión) ✅ |
| **Overhead** | Alto (reinicia proceso) | Mínimo ✅ |
| **Comunicación** | CLI subprocess | stdio persistente ✅ |

## Por qué `mcp_config.py` y `mcp_config_langchain.py` son claves

Estos módulos son la pieza de integración MCP para ambos enfoques.

- **Definen servidores SQL y NoSQL** en un punto central con sockets Unix.
- **Usan `socat`** para conectarse al socket del servidor ya levantado.
- **Evitan duplicar configuración** en cada agente.
- **Reutilizan la conexión persistente**: No reinician procesos.
- **Permiten cambiar comando/socket en un solo sitio**.

Flujo resumido:

1. Docker Compose levanta servidores MCP configurados con `socat UNIX-LISTEN` (Ej1).
2. Los servidores publican sus interfaces stdio en `/tmp/mcp-sockets/`.
3. El agente crea un cliente MCP (`MCPClient` o `MultiServerMCPClient`).
4. El cliente conecta vía `socat UNIX-CONNECT` a los sockets persistentes.
5. `get_tools()` devuelve herramientas MCP listas para el agente.
6. El agente ejecuta esas herramientas como si fueran locales.

## Requisitos previos

### 1. Docker Compose (Ej1) corriendo en background

Primero, asegúrate de tener los contenedores del Ej1 levantados:

```bash
cd ../Ej1-MCPServers

# Reconstruir con la nueva configuración (socat en Dockerfiles)
docker compose build

# Levantar en background
docker compose up -d

# Verificar que estén corriendo
docker compose ps
# Esperado: mcp_sql_service, mcp_nosql_service, mongodb, mongo_seeding en estado "Up"
```

### 2. Instalar `socat` en el host

`socat` es la herramienta que permite conectarse a los Unix sockets desde el host.

**En Linux (Debian/Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install -y socat
```

**Verificar instalación:**
```bash
socat -V
```

### 3. Instalar dependencias Python en Ej3

```bash
cd ../Ej3-MCPServers
python3 -m pip install -r requirements.txt
```

### 4. Definir credenciales de LLM (opcional, solo si usas agentes con LLM)

```bash
# Para smolagents
export HF_TOKEN="tu_token_huggingface"

# Para LangChain/LangGraph
export OPENAI_API_KEY="tu_api_key_openai"
export OPENAI_MODEL="gpt-4o-mini"              # Opcional
export OPENAI_BASE_URL="https://api.openai.com/v1"  # Opcional
```

## Verificacion de conectividad

Antes de ejecutar agentes, verifica que los sockets están siendo escuchados:

```bash
# Ver los sockets disponibles
ls -la /tmp/mcp-sockets/

# Esperado:
# sql.sock (Unix socket)
# nosql.sock (Unix socket)

# Probar conexión directa (debe responder sin error)
echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}' | \
  socat - UNIX-CONNECT:/tmp/mcp-sockets/sql.sock | head -1

# Esperado: respuesta JSON válida
```

## Pruebas rápidas (sin LLM)

Puedes validar cada agente con invocación directa de herramienta MCP **sin credenciales de LLM**:

```bash
# SQL directo (smolagents)
python3 agent_sql_mcp.py --direct-query "SELECT COUNT(*) FROM Artist;"

# NoSQL directo (smolagents)
python3 agent_nosql_mcp.py --direct-list

# SQL directo (LangChain/LangGraph)
python3 agent_sql_langchain_mcp.py --direct-query "SELECT COUNT(*) FROM Artist;"

# NoSQL directo (LangChain/LangGraph)
python3 agent_nosql_langchain_mcp.py --direct-list
```

## Ejecutar agentes con LLM (requiere credenciales)

### smolagents

#### SQL con agente

```bash
export HF_TOKEN="tu_token"
python3 agent_sql_mcp.py --prompt "Cuantos artistas hay en Chinook?"
```

#### NoSQL con agente

```bash
export HF_TOKEN="tu_token"
python3 agent_nosql_mcp.py --prompt "Que colecciones hay en MongoDB?"
```

### LangChain/LangGraph

#### SQL con agente

```bash
export OPENAI_API_KEY="tu_api_key"
python3 agent_sql_langchain_mcp.py --prompt "Cuantos artistas hay en Chinook?"
```

#### NoSQL con agente

```bash
export OPENAI_API_KEY="tu_api_key"
python3 agent_nosql_langchain_mcp.py --prompt "Que colecciones hay y cuantos documentos tienen?"
```

## Troubleshooting

### Error: "Permission denied" al conectar a socket

```
FileNotFoundError: [Errno 13] Permission denied: '/tmp/mcp-sockets/sql.sock'
```

**Solución:**
```bash
# Verificar permisos del socket
ls -la /tmp/mcp-sockets/sql.sock

# Deben tener permisos 777 o al menos para tu usuario
# Si no, reconstruir docker-compose:
cd ../Ej1-MCPServers
docker compose down -v
docker compose build
docker compose up -d
```

### Error: "Connection refused" al conectar a socket

```
errno 111: Connection refused
```

**Solución:**
```bash
# Verificar que los contenedores están corriendo
docker compose -f ../Ej1-MCPServers/docker-compose.yml ps

# Si no están UP, levantarlos:
cd ../Ej1-MCPServers
docker compose up -d

# Esperar a que estén listos (suele tardar ~5-10 segundos)
sleep 5

# Verificar socket nuevamente
ls -la /tmp/mcp-sockets/
```

### Error: "socat: command not found"

```
FileNotFoundError: [Errno 2] No such file or directory: 'socat'
```

**Solución:**
```bash
# Instalar socat en el host
sudo apt-get install -y socat

# Verificar
socat -V
```

### Error: LLM credentials not provided (smolagents)

```
EnvironmentError: Define HF_TOKEN para ejecutar el agente con LLM.
```

**Solución:**
```bash
export HF_TOKEN="tu_token_valido"
python3 agent_sql_mcp.py --prompt "..."
```

Para obtener token: https://huggingface.co/settings/tokens

### Error: LLM credentials not provided (LangChain)

```
EnvironmentError: Define OPENAI_API_KEY para ejecutar el agente con LLM.
```

**Solución:**
```bash
export OPENAI_API_KEY="tu_api_key_valida"
python3 agent_sql_langchain_mcp.py --prompt "..."
```

Para obtener API key: https://platform.openai.com/api-keys

## Notas importantes

- **Las opciones `--direct-*`** no requieren credenciales de LLM. Invocan la herramienta MCP directamente.
- **Las opciones `--prompt`** sí requieren credenciales del proveedor LLM.
- **Los contenedores deben estar corriendo** antes de ejecutar cualquier agente.
- **Los sockets persisten** mientras Docker Compose esté activo. Para limpiar:
  ```bash
  cd ../Ej1-MCPServers
  docker compose down -v
  ```
- **La comunicación es local (Unix sockets)**, no requiere TCP, HTTP ni acceso a red.
