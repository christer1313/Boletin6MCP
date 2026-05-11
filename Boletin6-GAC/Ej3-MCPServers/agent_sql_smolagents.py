import argparse
import os

from dotenv import load_dotenv

load_dotenv()

from smolagents import CodeAgent, LiteLLMModel, MCPClient

from mcp_config_smolagents import SQL_SERVER_PARAMS

# Agente SQL (smolagents) — usa MCP por Unix socket. Ver FLUJO_CONEXION_MCP.md


def build_model() -> LiteLLMModel:
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise EnvironmentError("Define HF_TOKEN para ejecutar el agente con LLM.")
    return LiteLLMModel(
        model_id="huggingface/Qwen/Qwen2.5-Coder-32B-Instruct",
        api_key=hf_token,
        temperature=0.2,
    )


def run_agent(prompt: str) -> str:
    """Ejecuta agente SQL con LLM usando herramientas MCP."""
    agent_instructions = (
        "Usa herramientas MCP solo con argumentos nombrados. "
        "Para SQL llama execute_sql_query(query=\"...\"). "
        "No uses argumentos posicionales en llamadas a tools."
    )
    # MCPClient se conecta al socket Unix y obtiene las herramientas
    with MCPClient(SQL_SERVER_PARAMS, structured_output=False) as tools:
        agent = CodeAgent(
            tools=tools,
            model=build_model(),
            add_base_tools=False,
        )
        return str(agent.run(f"{agent_instructions}\n\nPregunta del usuario: {prompt}"))


def run_direct_sql(query: str) -> str:
    """Ejecuta una query SQL directamente sin LLM."""
    with MCPClient(SQL_SERVER_PARAMS, structured_output=False) as tools:
        sql_tool = next(t for t in tools if t.name == "execute_sql_query")
        return str(sql_tool(query=query))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente SQL usando herramientas MCP")
    parser.add_argument(
        "--prompt",
        default="Cuantos artistas hay en Chinook?",
        help="Pregunta para el agente SQL.",
    )
    parser.add_argument(
        "--direct-query",
        default="",
        help="Si se indica, ejecuta esta query SQL directamente via MCP sin LLM.",
    )
    args = parser.parse_args()

    if args.direct_query:
        print(run_direct_sql(args.direct_query))
    else:
        print(run_agent(args.prompt))
