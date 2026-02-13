"""
LM-Proxy Application Entrypoint
"""

import logging
from typing import Optional
from fastapi import FastAPI
import typer
import uvicorn

from .bootstrap import env, bootstrap
from .core import chat_completions
from .models_endpoint import models
from .errors import OpenAIHTTPException


cli_app = typer.Typer()


@cli_app.callback(invoke_without_command=True)
def run_server(
    config: Optional[str] = typer.Option(None, help="Path to the configuration file"),
    debug: Optional[bool] = typer.Option(None, help="Enable debug mode (more verbose logging)"),
    env_file: Optional[str] = typer.Option(
        ".env",
        "--env",
        "--env-file",
        "--env_file",
        help="Set the .env file to load ENV vars from",
    ),
):
    """
    Default command for CLI application: Run LM-Proxy web server
    """
    try:
        bootstrap(config=config or "config.toml", env_file=env_file, debug=debug)
        uvicorn.run(
            "lm_proxy.app:web_app",
            host=env.config.host,
            port=env.config.port,
            ssl_keyfile=env.config.ssl_keyfile or None,
            ssl_certfile=env.config.ssl_certfile or None,
            reload=env.config.dev_autoreload,
            factory=True,
        )
    except Exception as e:
        if env.debug:
            raise
        logging.error(e)
        raise typer.Exit(code=1)


def web_app():
    """
    Entrypoint for ASGI server
    """
    app = FastAPI(title="LM-Proxy", description="OpenAI-compatible proxy server for LLM inference")
    OpenAIHTTPException.register(app)
    app.add_api_route(
        path=f"{env.config.api_prefix}/chat/completions",
        endpoint=chat_completions,
        methods=["POST"],
    )
    app.add_api_route(
        path=f"{env.config.api_prefix}/models",
        endpoint=models,
        methods=["GET"],
    )
    return app


if __name__ == "__main__":
    cli_app()
