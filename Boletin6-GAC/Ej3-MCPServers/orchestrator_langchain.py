import asyncio
import json
import os
import re
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END, START
from langgraph.types import Command
from typing_extensions import TypedDict

from agent_sql_langchain import execute_sql_query, build_model as build_sql_model
from agent_nosql_langchain import list_collections, query_mongo, build_model as build_nosql_model

# Orquestador LangChain (LangGraph) con Router Agent inteligente
# Ver FLUJO_CONEXION_MCP.md y README.md para detalles


# ═══════════════════════════════════════════════════════════════════════════
# SCHEMAS: Especificaciones de herramientas disponibles
# ═══════════════════════════════════════════════════════════════════════════

TOOL_SCHEMAS = {
    "sql": {
        "description": "Herramientas SQL para base de datos Chinook",
        "tools": [
            {
                "name": "execute_sql_query",
                "description": "Ejecuta queries SQL en Chinook.sqlite",
                "tables": ["Artist", "Album", "Track", "Genre", "Customer", "Order", "OrderDetail"],
                "example": "SELECT * FROM Artist WHERE Name LIKE 'A%'"
            }
        ]
    },
    "nosql": {
        "description": "Herramientas MongoDB para acceso a colecciones",
        "tools": [
            {
                "name": "list_collections",
                "description": "Lista todas las colecciones disponibles en MongoDB"
            },
            {
                "name": "query_mongo",
                "description": "Accede a colecciones MongoDB con filtros",
                "example": "db.usuarios.find({edad: {$gt: 18}})"
            }
        ]
    }
}


class OrchestratorState(TypedDict):
    """Estado que fluye a través del grafo LangGraph."""
    user_query: str
    router_decision: Literal["sql", "nosql", "both", "error"]
    router_reasoning: str
    sql_result: str
    nosql_result: str
    final_response: str


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER AGENT: Analiza la petición y decide qué tools usar
# ═══════════════════════════════════════════════════════════════════════════

def get_schema(db_type: Literal["sql", "nosql", "both"] = "both") -> str:
    """Obtiene las especificaciones de las herramientas disponibles.
    
    Úsalo para verificar qué tablas/colecciones están disponibles.
    """
    if db_type == "both":
        return json.dumps(TOOL_SCHEMAS, indent=2)
    return json.dumps(TOOL_SCHEMAS.get(db_type, {}), indent=2)


async def translate_question_to_sql(user_question: str) -> str:
    """Traduce una pregunta a una query SQL usando LLM."""
    model = build_sql_model()
    schema = get_schema("sql")
    
    prompt = f"""Eres un experto en SQL para la base de datos Chinook.

Esquema disponible:
{schema}

Pregunta del usuario: "{user_question}"

Genera SOLO la query SQL (sin explicaciones, sin markdown, solo el SQL puro).
Asegúrate de que sea una query válida.
"""
    
    result = await model.ainvoke([
        SystemMessage(content="Eres un experto en SQL."),
        HumanMessage(content=prompt),
    ])
    response_text = getattr(result, "content", str(result)).strip()
    # Limpiar posibles markers de código
    response_text = response_text.replace("```sql", "").replace("```", "").strip()
    return response_text


async def translate_question_to_nosql(user_question: str) -> str:
    """Traduce una pregunta a operaciones NoSQL usando LLM."""
    model = build_nosql_model()
    schema = get_schema("nosql")
    
    prompt = f"""Eres un experto en MongoDB.

Esquema disponible:
{schema}

Pregunta del usuario: "{user_question}"

Responde con qué colección acceder y proporciona el resultado de listar colecciones o un query si aplica.
Devuelve un JSON con formato: {{"action": "list_collections" | "query_mongo", "collection": "...", "filter": {{...}}}}
"""
    
    result = await model.ainvoke([SystemMessage(content=prompt)])
    response_text = getattr(result, "content", str(result)).strip()
    return response_text


def build_router_model():
    """Router usa un único modelo Ollama para mantener la arquitectura simple."""
    ollama_api_key = os.getenv("OLLAMA_API_KEY")
    if not ollama_api_key:
        raise EnvironmentError("Define OLLAMA_API_KEY para ejecutar LangChain con Ollama.")

    model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")
    return ChatOllama(
        model=model_name,
        base_url=os.getenv("OLLAMA_BASE_URL", "https://ollama.com"),
        headers={"Authorization": f"Bearer {ollama_api_key}"},
        temperature=0,
    )


def _extract_json_payload(text: str) -> str:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        return match.group(0)
    return text.strip()


async def router_node(state: OrchestratorState) -> OrchestratorState:
    """Nodo Router: Analiza la petición del usuario y decide qué herramientas usar.
    
    El router tiene acceso a get_schema para explorar qué está disponible.
    """
    schema = get_schema("both")
    router_model = build_router_model()

    prompt = f"""Eres un router inteligente.

Tu job: Analizar la petición del usuario y decidir si necesita:
- "sql": ejecutar queries en base de datos SQL (Chinook)
- "nosql": acceder a colecciones MongoDB
- "both": necesita ambas
- "error": la petición es inválida

Esquema disponible:
{schema}

Petición del usuario: "{state['user_query']}"

Analiza:
1. ¿Menciona tablas SQL (Artist, Album, Track, etc)?
2. ¿Menciona colecciones MongoDB?
3. ¿Necesita combinar datos de ambas?

Responde en JSON:
{{"decision": "sql|nosql|both|error", "reasoning": "tu análisis aquí"}}"""

    result = await router_model.ainvoke([
        SystemMessage(content="Responde solo con JSON válido."),
        HumanMessage(content=prompt),
    ])

    response_text = getattr(result, "content", str(result))
    
    try:
        json_response = json.loads(_extract_json_payload(response_text))
        state["router_decision"] = json_response.get("decision", "error")
        state["router_reasoning"] = json_response.get("reasoning", "")
    except json.JSONDecodeError:
        state["router_decision"] = "error"
        state["router_reasoning"] = f"Router no pudo parsear: {response_text}"
    
    return state


# ═══════════════════════════════════════════════════════════════════════════
# AGENTES ESPECIALIZADOS
# ═══════════════════════════════════════════════════════════════════════════

async def sql_agent_node(state: OrchestratorState) -> OrchestratorState:
    """Ejecuta agente SQL si es necesario."""
    if state["router_decision"] in ["sql", "both"]:
        try:
            # Translate question to SQL, then execute
            sql_query = await translate_question_to_sql(state["user_query"])
            state["sql_result"] = await execute_sql_query(sql_query)
        except Exception as e:
            state["sql_result"] = f"Error en SQL: {str(e)}"
    return state


async def nosql_agent_node(state: OrchestratorState) -> OrchestratorState:
    """Ejecuta agente NoSQL si es necesario."""
    if state["router_decision"] in ["nosql", "both"]:
        try:
            # Intenta listar colecciones como primer paso
            state["nosql_result"] = await list_collections()
        except Exception as e:
            state["nosql_result"] = f"Error en NoSQL: {str(e)}"
    return state


async def both_agents_node(state: OrchestratorState) -> OrchestratorState:
    """Ejecuta ambos agentes (SQL y NoSQL)."""
    try:
        sql_query = await translate_question_to_sql(state["user_query"])
        state["sql_result"] = await execute_sql_query(sql_query)
    except Exception as e:
        state["sql_result"] = f"Error en SQL: {str(e)}"
    
    try:
        state["nosql_result"] = await list_collections()
    except Exception as e:
        state["nosql_result"] = f"Error en NoSQL: {str(e)}"
    
    return state


async def combine_node(state: OrchestratorState) -> OrchestratorState:
    """Combina resultados de ambos agentes si es necesario."""
    if state["router_decision"] == "error":
        state["final_response"] = f"Error: {state['router_reasoning']}"
    elif state["router_decision"] == "sql":
        state["final_response"] = state.get("sql_result", "Sin resultado SQL")
    elif state["router_decision"] == "nosql":
        state["final_response"] = state.get("nosql_result", "Sin resultado NoSQL")
    elif state["router_decision"] == "both":
        state["final_response"] = f"""
SQL:
{state.get('sql_result', 'Sin resultado')}

NoSQL:
{state.get('nosql_result', 'Sin resultado')}
""".strip()
    else:
        state["final_response"] = "Decisión del router inválida"
    
    return state


async def both_agents_node(state: OrchestratorState) -> OrchestratorState:
    """Ejecuta ambos agentes en paralelo."""
    try:
        state["sql_result"] = await execute_sql_query(state["user_query"])
    except Exception as e:
        state["sql_result"] = f"Error en SQL: {str(e)}"
    
    try:
        state["nosql_result"] = await list_collections()
    except Exception as e:
        state["nosql_result"] = f"Error en NoSQL: {str(e)}"
    
    return state


# ═══════════════════════════════════════════════════════════════════════════
# GRAFO LANGGRAPH
# ═══════════════════════════════════════════════════════════════════════════

async def run_orchestrator(user_query: str) -> str:
    """Ejecuta la orquestación completa."""
    
    # Crear grafo
    graph = StateGraph(OrchestratorState)
    
    # Agregar nodos
    graph.add_node("router", router_node)
    graph.add_node("sql_agent", sql_agent_node)
    graph.add_node("nosql_agent", nosql_agent_node)
    graph.add_node("both_agents", both_agents_node)
    graph.add_node("combine", combine_node)
    
    # Agregar aristas desde START
    graph.add_edge(START, "router")
    
    # Routing condicional basado en decisión
    def route_decision(state: OrchestratorState) -> str:
        decision = state["router_decision"]
        if decision == "sql":
            return "sql_agent"
        elif decision == "nosql":
            return "nosql_agent"
        elif decision == "both":
            return "both_agents"
        else:
            return "combine"
    
    graph.add_conditional_edges("router", route_decision, {
        "sql_agent": "sql_agent",
        "nosql_agent": "nosql_agent",
        "both_agents": "both_agents",
        "combine": "combine"
    })
    
    # Aristas de los agentes a combine
    graph.add_edge("sql_agent", "combine")
    graph.add_edge("nosql_agent", "combine")
    graph.add_edge("both_agents", "combine")
    graph.add_edge("combine", END)
    
    # Compilar y ejecutar
    app = graph.compile()
    
    initial_state = OrchestratorState(
        user_query=user_query,
        router_decision="error",
        router_reasoning="",
        sql_result="",
        nosql_result="",
        final_response=""
    )
    
    result = await app.ainvoke(initial_state)
    
    return result["final_response"]


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Orquestador LangChain/LangGraph con Router inteligente"
    )
    parser.add_argument("--query", required=True, help="Pregunta para el orquestador")
    args = parser.parse_args()
    
    result = asyncio.run(run_orchestrator(args.query))
    print(result)
