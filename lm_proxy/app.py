import asyncio
import logging
import json
import os
from contextlib import asynccontextmanager
from typing import Callable, Dict, Any, AsyncGenerator, Literal, List, Optional

import microcore as mc
from microcore.configuration import get_bool_from_env
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from starlette.responses import JSONResponse
from pydantic import BaseModel
import secrets
import time

from .bootstrap import bootstrap


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

@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap()
    yield

app = FastAPI(
    title="LM-Proxy",
    description="OpenAI-compatible proxy server for LLM inference",
    lifespan=lifespan,
)

async def process_stream(prompt, llm_params):
    queue = asyncio.Queue()
    stream_id = f"chatcmpl-{secrets.token_hex(12)}"
    created = int(time.time())
    model = llm_params.get("model", "unknown")

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
        mc.allm(prompt, **llm_params, callback=callback)
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

    if get_bool_from_env("LM_PROXY_OVERWRITE_MODEL", False):
        llm_params['model'] = mc.config().MODEL

    logging.info("Querying LLM... params: %s", llm_params)
    if request.stream:
        return StreamingResponse(
            process_stream(request.messages, llm_params),
            media_type="text/event-stream"
        )
    out = await mc.allm(request.messages, **llm_params)
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
    from uvicorn_start import uvicorn_start
    uvicorn_start()