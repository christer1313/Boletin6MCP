import argparse
import os

from smolagents import CodeAgent, LiteLLMModel, MCPClient

from mcp_config import SQL_SERVER_PARAMS


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
    # MCP tools requieren argumentos nombrados (keyword args), no posicionales.
    agent_instructions = (
        "Usa herramientas MCP solo con argumentos nombrados. "
        "Para SQL llama execute_sql_query(query=\"...\"). "
        "No uses argumentos posicionales en llamadas a tools."
    )
    with MCPClient(SQL_SERVER_PARAMS, structured_output=False) as tools:
        agent = CodeAgent(
            tools=tools,
            model=build_model(),
            add_base_tools=False,
        )
        return str(agent.run(f"{agent_instructions}\n\nPregunta del usuario: {prompt}"))


def run_direct_sql(query: str) -> str:
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
