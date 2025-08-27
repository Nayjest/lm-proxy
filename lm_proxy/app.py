import asyncio
import logging
import json
import os
import sys
import secrets
import time
import fnmatch
from contextlib import asynccontextmanager
from typing import Callable, Dict, Any, AsyncGenerator, Literal, List, Optional

import microcore as mc
from microcore.configuration import get_bool_from_env
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from my_nlq.cli_app import cli_app
from starlette.responses import JSONResponse
from pydantic import BaseModel
import typer

from .bootstrap import Env
from .config import Config


cli_app = typer.Typer()
config_file: str = "config.toml"
env: Env = None


def resolve_connection_and_model(config: Config, external_model: str) -> tuple[str, str]:
    for model_match, rule in config.routing.items():
        if fnmatch.fnmatchcase(external_model, model_match):
            connection_name, model_part = rule.split(".", 1)
            if connection_name not in config.connections:
                raise ValueError(
                    f"Routing selected unknown connection '{connection_name}'. "
                    f"Defined connections: {', '.join(config.connections.keys()) or '(none)'}"
                )

            resolved_model = external_model if model_part == "*" else rhs_model
            return connection_name, resolved_model

    raise ValueError(
        f"No routing rule matched model '{external_model}'. "
        "Add a catch-all rule like \"*\" = \"openai.gpt-3.5-turbo\" if desired."
    )


# make run-server default command
@cli_app.callback(invoke_without_command=True)
def run_server(
    config: str = typer.Option(None, help="Path to the configuration file"),
):
    if config:
        global config_file
        config_file = config
    from uvicorn_start import uvicorn_start
    uvicorn_start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global env
    env = Env.bootstrap(config_file)
    yield

app = FastAPI(
    title="LM-Proxy",
    description="OpenAI-compatible proxy server for LLM inference",
    lifespan=lifespan,
)


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[mc.Msg]
    stream: Optional[bool] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stop: Optional[List[str]] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    user: Optional[str] = None


async def process_stream(async_llm_func, prompt, llm_params):
    queue = asyncio.Queue()
    stream_id = f"chatcmpl-{secrets.token_hex(12)}"
    created = int(time.time())
    model = llm_params.get("model", "default_model")

    async def callback(chunk):
        await queue.put(chunk)

    def make_chunk(delta = None, content = None, finish_reason = None, error = None) -> str:
        if delta is None:
            delta = dict(content=str(content)) if content is not None else dict()
        obj = {
            "id": stream_id,
            "object": "chat.completion.chunk",
            "created": created,
            "choices": [{"index": 0, "delta": delta}],
        }
        if error is not None:
            obj['error'] = {'message': str(error), 'type': type(error).__name__}
            if finish_reason is None:
                finish_reason = 'error'
        if finish_reason is not None:
            obj['choices'][0]['finish_reason'] = finish_reason
        return "data: " + json.dumps(obj) + "\n\n"

    task = asyncio.create_task(
        async_llm_func(prompt, **llm_params, callback=callback)
    )

    try:
        # Initial chunk: role
        yield make_chunk(delta={'role':'assistant'})

        while not task.done():
            try:
                block = await asyncio.wait_for(queue.get(), timeout=0.1)
                yield make_chunk(content=block)
            except asyncio.TimeoutError:
                continue

        # Drain any remaining
        while not queue.empty():
            block = await queue.get()
            yield make_chunk(content=block)

    finally:
        try:
            await task
        except Exception as e:
            yield make_chunk(error={'message': str(e), 'type': type(e).__name__})

    # Final chunk: finish_reason
    yield make_chunk(finish_reason='stop')
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest) -> Response:
    """
    Endpoint for chat completions that mimics OpenAI's API structure.
    Streams the response from the LLM using microcore.
    """
    llm_params = request.dict(exclude=['messages'], exclude_none=True)

    connection, llm_params["model"] = resolve_connection_and_model(
        env.config,
        llm_params.get("model", "default_model")
    )
    async_llm_func = env.connections[connection]

    logging.info("Querying LLM... params: %s", llm_params)
    if request.stream:
        return StreamingResponse(
            process_stream(async_llm_func, request.messages, llm_params),
            media_type="text/event-stream"
        )
    out = await async_llm_func(request.messages, **llm_params)
    logging.info("LLM response: %s", out)
    return JSONResponse(
        {
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": str(out)},
                    "finish_reason": "stop"
                }
            ]
        }
    )


if __name__ == "__main__":
    run_server()