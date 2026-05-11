# Arquitectura del Orquestador: Router Agent + LangGraph

## Visión General

El **Orquestador** es un sistema inteligente de 3 capas que analiza preguntas del usuario en lenguaje natural y automáticamente elige qué herramientas MCP usar:

```
┌──────────────────────────────────────────────────────┐
│         Usuario: "Cuantos artistas hay?"             │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  1️⃣  ROUTER AGENT (Decisor Inteligente)             │
│  ├─ Lee la pregunta                                 │
│  ├─ Llama get_schema() para explorar datos          │
│  ├─ Analiza: "artistas" → busca en schema           │
│  └─ Retorna: {"decision": "sql", ...}               │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ Decisión: ¿"sql"?   │
        │   ▼ Sí (ejecutar)   │
        │   ▼ No (saltar)     │
        └─────────────────────┘
                   │
         ____________│____________
        │                        │
        ▼                        ▼
┌─────────────────┐     ┌─────────────────┐
│2️⃣  SQL AGENT    │     │2️⃣  NOSQL AGENT │
│                 │     │                 │
│execute_sql_... │     │list_collections │
│query("SELECT") │     │query_mongo()    │
│                 │     │                 │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └──────────┬────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │3️⃣  COMBINE RESULTS      │
        │  ├─ sql_result: "..."   │
        │  ├─ nosql_result: "..." │
        │  └─ final_response: "..." 
        └──────────────┬──────────┘
                       │
                       ▼
        ┌──────────────────────────┐
        │ Respuesta al usuario     │
        │ "Total: 275 artistas"    │
        └──────────────────────────┘
```

---

## Capa 1: Router Agent (Decisor)

### Responsabilidad
Analizar la pregunta del usuario y decidir:
- **"sql"**: enviar a agent_sql_langchain
- **"nosql"**: enviar a agent_nosql_langchain  
- **"both"**: ejecutar ambos en paralelo
- **"error"**: pregunta inválida

### Mecanismo de Decisión

#### 1. Acceso a `get_schema()`
El router tiene acceso exclusivo a una herramienta especial que devuelve:

```python
TOOL_SCHEMAS = {
    "sql": {
        "tools": [
            {
                "name": "execute_sql_query",
                "tables": ["Artist", "Album", "Track", "Genre", ...]
            }
        ]
    },
    "nosql": {
        "tools": [
            {
                "name": "list_collections",
                "description": "Lista colecciones en MongoDB"
            }
        ]
    }
}
```

#### 2. Análisis de la Query

El router (ejecutado por LLM):
1. **Lee** la pregunta: "Cuantos artistas hay?"
2. **Llama** `get_schema()` para ver qué está disponible
3. **Identifica** palabras clave: "artistas" → tabla "Artist" en SQL
4. **Decide**: ruta = "sql"
5. **Retorna**: JSON con decision + reasoning

Ejemplo de routing inteligente:

| Query | get_schema() llamado | Decisión | Reasoning |
|-------|------------------|----------|-----------|
| "Listar artistas" | Sí → SQL tables | "sql" | "Artist" tabla en SQL |
| "Que collections en MongoDB" | Sí → nosql tools | "nosql" | "MongoDB" mencionado explícitamente |
| "Compara artistas SQL vs docs Mongo" | Sí → ambos | "both" | Ambas BDs mencionadas |

### Código del Router

```python
# En orchestrator_langchain.py
async def router_node(state: OrchestratorState) -> OrchestratorState:
    """
    Usa create_react_agent(model, [get_schema]) para que el router:
    - Tenga acceso a get_schema()
    - Analice la query
    - Devuelva JSON con decision
    """
    tools = [get_schema]  # ← Herramienta exclusiva del router
    router_agent = create_react_agent(build_router_model(), tools)
    
    # El router usa ReAct: razón → usa get_schema() → decide
    result = await router_agent.ainvoke({"messages": [...]})
    
    # Parsear JSON y actualizar state["router_decision"]
    return state
```

### Por qué `get_schema()` es crítica

Sin `get_schema()`:
```python
# ❌ Heurístico fallible
if "artist" in user_query.lower():
    decision = "sql"
# Problema: ¿y si el usuario pregunta sobre "artists" en MongoDB?
```

Con `get_schema()`:
```python
# ✅ Basado en hechos
schemas = get_schema("both")
if "artist" in user_query and "Artist" in schemas["sql"]["tables"]:
    decision = "sql"
# Caso correcto: solo decido SQL si la tabla existe
```

---

## Capa 2: Agentes Especializados

### agent_sql_langchain.py
- **Propósito**: Expert en SQL (Chinook.sqlite)
- **Herramientas**: solo `execute_sql_query`
- **Contexto**: limitado a esquema SQL único
- **Ventaja**: Evita confundir tools NoSQL en SQL queries

```python
async def execute_sql_query(query: str) -> str:
    """Ejecuta SQL directamente sin dudas sobre MongoDB"""
    tools = await get_tools()  # Solo SQL tools
    sql_tool = next(t for t in tools if t.name == "execute_sql_query")
    return str(await sql_tool.ainvoke({"query": query}))
```

### agent_nosql_langchain.py
- **Propósito**: Expert en NoSQL (MongoDB)
- **Herramientas**: `list_collections`, `query_mongo`
- **Contexto**: limitado a esquema MongoDB único
- **Ventaja**: Evita confundir SQL syntax en NoSQL queries

```python
async def query_mongo(collection_name: str, query_filter: dict) -> str:
    """Accede MongoDB directamente sin confusión de sintaxis"""
    tools = await get_tools()  # Solo NoSQL tools
    query_tool = next(t for t in tools if t.name == "query_mongo")
    return str(await query_tool.ainvoke(payload))
```

### Ventaja de Especialización

```
┌────────────────────────────────────────────────────────┐
│ Generalist Agent (antipatrón)                          │
│                                                         │
│ tools = [execute_sql_query, list_collections,          │
│          query_mongo, ...]  ← Demasiadas               │
│                                                         │
│ LLM context:                                            │
│ ❌ "qué tool usar para 'artistas'?"                    │
│ ❌ Puede mezclar SQL syntax con MongoDB                │
│ ❌ Más hallucinations, más errores                     │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ Specialized Agents (recomendado)                        │
│                                                         │
│ SQL Agent:             NoSQL Agent:                    │
│ tools = [execute]      tools = [list, query]           │
│                                                         │
│ LLM context:           LLM context:                    │
│ ✅ "Cómo ejecuto      ✅ "Cómo acceso                 │
│     esto en SQL?"     MongoDB?"                         │
│ ✅ Sintaxis SQL       ✅ Sintaxis MongoDB              │
│    clara               clara                           │
│ ✅ Menor error rate   ✅ Menor error rate              │
└────────────────────────────────────────────────────────┘
```

---

## Capa 3: Combinador de Resultados

### Responsabilidad
Unir las respuestas de SQL y/o NoSQL agentes en una respuesta coherente.

### Lógica

```python
async def combine_node(state: OrchestratorState) -> OrchestratorState:
    if state["router_decision"] == "sql":
        # Solo SQL → devolver resultado SQL
        state["final_response"] = state["sql_result"]
    
    elif state["router_decision"] == "nosql":
        # Solo NoSQL → devolver resultado NoSQL
        state["final_response"] = state["nosql_result"]
    
    elif state["router_decision"] == "both":
        # Ambas → combinar con formato legible
        state["final_response"] = f"""
Resultados SQL:
{state['sql_result']}

Resultados NoSQL:
{state['nosql_result']}
""".strip()
    
    return state
```

---

## Grafo LangGraph

La orquestación se implementa como un **state machine**:

```python
graph = StateGraph(OrchestratorState)

# Nodos
graph.add_node("router", router_node)
graph.add_node("sql_agent", sql_agent_node)
graph.add_node("nosql_agent", nosql_agent_node)
graph.add_node("combine", combine_node)

# Aristas (siempre pasan por router primero)
graph.add_edge("router", "sql_agent")
graph.add_edge("router", "nosql_agent")
graph.add_edge("sql_agent", "combine")
graph.add_edge("nosql_agent", "combine")
graph.add_edge("combine", END)

app = graph.compile()
result = await app.ainvoke(initial_state)
```

### Flujo de Ejecución

```
START
  │
  ▼
ROUTER (parse query + get_schema)
  │
  ├─ decision="sql" ──→ SQL_AGENT ──┐
  │                                  │
  ├─ decision="nosql" ─→ NOSQL_AGENT ├─→ COMBINE ──→ END
  │                                  │
  └─ decision="both" ─→ ambos ───────┘
```

### Paralelismo

Si router decide "both":
- SQL_AGENT y NOSQL_AGENT ejecutan **en paralelo**
- LangGraph maneja sincronización automáticamente
- COMBINE espera a ambos completar

**Velocidad:**
- Secuencial: 2 * (duración query) = 2 * 5s = 10s
- Paralelo: max(duración query 1, query 2) = 5s ✅

---

## State: OrchestratorState

```python
class OrchestratorState(TypedDict):
    user_query: str          # "Cuantos artistas hay?"
    router_decision: str     # "sql" | "nosql" | "both" | "error"
    router_reasoning: str    # "Encontré 'artistas' en tabla Artist"
    sql_result: str         # Resultado de SQL si aplica
    nosql_result: str       # Resultado de NoSQL si aplica
    final_response: str     # Respuesta final enviada al usuario
```

Cada nodo puede leer y escribir `state`. LangGraph garantiza que sea thread-safe.

---

## Flujos de Ejemplo

### Ejemplo 1: Query SQL Puro

```
User: "¿Cuantos artistas hay en Chinook?"

1. router_node():
   - Llama get_schema("both")
   - Lee "artistas" → encuentra tabla "Artist" en SQL
   - Retorna: {"decision": "sql", "reasoning": "..."}

2. sql_agent_node():
   - Ejecuta: execute_sql_query("¿Cuantos artistas hay en Chinook?")
   - LLM (SQL agent) genera: SELECT COUNT(*) FROM Artist;
   - Resultado: 275

3. nosql_agent_node():
   - Se salta (decision no es "nosql" ni "both")

4. combine_node():
   - Retorna: "275 artistas en total"

Result: "275 artistas en total"
```

### Ejemplo 2: Query Combinada

```
User: "Compara el número de artistas en SQL con documentos en MongoDB"

1. router_node():
   - Llama get_schema("both")
   - Lee ambas menciones
   - Retorna: {"decision": "both", "reasoning": "..."}

2. sql_agent_node() + nosql_agent_node() [PARALELOS]:
   - SQL: "275 artistas"
   - NoSQL: "50 documentos"

3. combine_node():
   - Retorna formateado

Result:
"Resultados SQL:
275 artistas

Resultados NoSQL:
50 documentos

Comparación: SQL tiene 5.5x más registros"
```

---

## Testing

### Script: `test_orchestrator.py`

Valida cada capa:

```bash
# Test 1-3: Infraestructura (sockets, imports, credenciales)
# Test 4-5: Agentes individuales (SQL, NoSQL)
# Test 6: Router + get_schema()
# Test 7: Orquestación completa

python3 test_orchestrator.py
```

---

## Ventajas de esta Arquitectura

| Aspecto | Solución Anterior | Arquitectura Actual |
|--------|------------------|-----------------|
| **Tool confusion** | ❌ Todos tools en contexto | ✅ Solo tools relevantes |
| **Routing** | ❌ Heurístico (regex) | ✅ Schema-aware (get_schema) |
| **Paralelismo** | ❌ Secuencial forzado | ✅ Paralelo automático |
| **Escalabilidad** | ❌ Agregar una BD = reescribir prompts | ✅ Agregar herramienta MCP = actualizar schema |
| **Debugging** | ❌ Todo junto = difícil aislar | ✅ Cada nodo es aislable |
| **Mantenibilidad** | ❌ Código monolítico | ✅ Capas claras + LangGraph explicit |

---

## Referencias

- **FLUJO_CONEXION_MCP.md**: Cómo los clientes conectan a MCP servers vía Unix sockets
- **orchestrator_langchain.py**: Código fuente del orquestador
- **agent_sql_langchain.py**: Implementación del agente SQL
- **agent_nosql_langchain.py**: Implementación del agente NoSQL
- **test_orchestrator.py**: Suite de validación
