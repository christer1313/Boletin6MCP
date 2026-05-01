import argparse
import os

from smolagents import CodeAgent, LiteLLMModel, MCPClient

from mcp_config import NOSQL_SERVER_PARAMS


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
    with MCPClient(NOSQL_SERVER_PARAMS, structured_output=False) as tools:
        agent = CodeAgent(
            tools=tools,
            model=build_model(),
            add_base_tools=False,
        )
        return str(agent.run(prompt))


def run_direct_list_collections() -> str:
    with MCPClient(NOSQL_SERVER_PARAMS, structured_output=False) as tools:
        list_tool = next(t for t in tools if t.name == "list_collections")
        return str(list_tool())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente NoSQL usando herramientas MCP")
    parser.add_argument(
        "--prompt",
        default="Que colecciones hay en MongoDB?",
        help="Pregunta para el agente NoSQL.",
    )
    parser.add_argument(
        "--direct-list",
        action="store_true",
        help="Si se activa, lista colecciones directamente via MCP sin LLM.",
    )
    args = parser.parse_args()

    if args.direct_list:
        print(run_direct_list_collections())
    else:
        print(run_agent(args.prompt))
