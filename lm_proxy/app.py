from fastapi import FastAPI
import typer
import uvicorn

from .bootstrap import env, bootstrap
from .core import chat_completions

cli_app = typer.Typer()


# run-server is a default command of cli-app
@cli_app.callback(invoke_without_command=True)
def run_server(
    config: str = typer.Option(None, help="Path to the configuration file"),
    debug: bool = typer.Option(False, help="Enable debug mode (more verbose logging)"),
):
    bootstrap(config or 'config.toml')
    uvicorn.run(
        "lm_proxy.app:web_app",
        host=env.config.host,
        port=env.config.port,
        reload=env.config.dev_autoreload,
    )


def web_app():
    app = FastAPI(title="LM-Proxy", description="OpenAI-compatible proxy server for LLM inference")
    app.add_api_route(
        path="/v1/chat/completions",
        endpoint=chat_completions,
        methods=["POST"],
    )
    return app


if __name__ == "__main__":
    cli_app()
