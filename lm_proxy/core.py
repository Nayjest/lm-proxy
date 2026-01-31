"""Core LM-Proxy logic"""
import asyncio
import fnmatch
import json
import logging
import secrets
import time
import hashlib
from datetime import datetime
from typing import Optional, Callable, Awaitable

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from .base_types import ChatCompletionRequest, RequestContext
from .bootstrap import env
from .config import Config
from .utils import get_client_ip
from .middleware import run_middleware_chain


def parse_routing_rule(rule: str, config: Config) -> tuple[str, str]:
    """
    Parses a routing rule in the format 'connection.model' or 'connection.*'.
    Returns a tuple of (connection_name, model_part).
    Args:
        rule (str): The routing rule string.
        config (Config): The configuration object containing defined connections.
    Raises:
        ValueError: If the rule format is invalid or the connection is unknown.
    """
    if "." not in rule:
        raise ValueError(
            f"Invalid routing rule '{rule}'. Expected format: 'connection.model' or 'connection.*'"
        )
    connection_name, model_part = rule.split(".", 1)
    if connection_name not in config.connections:
        raise ValueError(
            f"Routing selected unknown connection '{connection_name}'. "
            f"Defined connections: {', '.join(config.connections.keys()) or '(none)'}"
        )
    return connection_name, model_part


def resolve_connection_and_model(
    config: Config, external_model: str
) -> tuple[str, str]:
    """
    Resolves the connection name and model name based on routing rules.
    Args:
        config (Config): The configuration object containing routing rules.
        external_model (str): The external model name from the request.
    """
    for model_match, rule in config.routing.items():
        if fnmatch.fnmatchcase(external_model, model_match):
            connection_name, model_part = parse_routing_rule(rule, config)
            resolved_model = external_model if model_part == "*" else model_part
            return connection_name, resolved_model

    raise ValueError(
        f"No routing rule matched model '{external_model}'. "
        'Add a catch-all rule like "*" = "openai.gpt-3.5-turbo" if desired.'
    )


async def process_stream(
    async_llm_func,
    request: ChatCompletionRequest,
    llm_params,
    ctx: RequestContext,
    on_complete: Callable[[], Awaitable[None]] | None = None,
):
    """
    Streams the response from the LLM function.
    """
    prompt = request.messages
    queue = asyncio.Queue()
    stream_id = f"chatcmpl-{secrets.token_hex(12)}"
    created = int(time.time())

    async def callback(chunk):
        await queue.put(chunk)

    def make_chunk(delta=None, content=None, finish_reason=None, error=None) -> str:
        if delta is None:
            delta = {"content": str(content)} if content is not None else {}
        obj = {
            "id": stream_id,
            "object": "chat.completion.chunk",
            "created": created,
            "choices": [{"index": 0, "delta": delta}],
        }
        if error is not None:
            obj["error"] = {"message": str(error), "type": type(error).__name__}
            if finish_reason is None:
                finish_reason = "error"
        if finish_reason is not None:
            obj["choices"][0]["finish_reason"] = finish_reason
        return "data: " + json.dumps(obj) + "\n\n"

    task = asyncio.create_task(async_llm_func(prompt, **llm_params, callback=callback))

    try:
        yield make_chunk(delta={"role": "assistant"})

        while not task.done():
            try:
                block = await asyncio.wait_for(queue.get(), timeout=0.1)
                yield make_chunk(content=block)
            except asyncio.TimeoutError:
                continue

        while not queue.empty():
            block = await queue.get()
            yield make_chunk(content=block)

    finally:
        try:
            result = await task
            ctx.response = result
        except Exception as e:
            ctx.error = e
            yield make_chunk(error={"message": str(e), "type": type(e).__name__})

    yield make_chunk(finish_reason="error" if ctx.error else "stop")
    yield "data: [DONE]\n\n"

    if on_complete:
        await on_complete()  # Middleware "after" + logging happens here

    if ctx.error and env.debug:
        raise ctx.error


def read_api_key(request: Request) -> str:
    """
    Extracts the Bearer token from the Authorization header.
    returns '' if not present.
    """
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def api_key_id(api_key: Optional[str]) -> str | None:
    """
    Generates a consistent hashed identifier for the given API key.
    """
    if not api_key:
        return None
    return hashlib.md5(
        (api_key + env.config.encryption_key).encode("utf-8")
    ).hexdigest()


async def check(request: Request) -> tuple[str, str, dict]:
    """
    API key and service availability check for endpoints.
    Args:
        request (Request): The incoming HTTP request object.
    Returns:
        tuple[str, str, dict]: A tuple containing the group name, the API key and user_info object.
    Raises:
        HTTPException: If the service is disabled or the API key is invalid.
    """
    if not env.config.enabled:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "message": "The service is disabled.",
                    "type": "service_unavailable",
                    "param": None,
                    "code": "service_disabled",
                }
            },
        )
    api_key = read_api_key(request)
    result = (env.config.api_key_check)(api_key)
    if isinstance(result, tuple):
        group, user_info = result
    else:
        group: str | bool | None = result
        user_info = {}

    if not group:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "message": "Incorrect API key provided: "
                    "your API key is invalid, expired, or revoked.",
                    "type": "invalid_request_error",
                    "param": None,
                    "code": "invalid_api_key",
                }
            },
        )
    return group, api_key, user_info


async def chat_completions(
    request: ChatCompletionRequest, raw_request: Request
) -> Response:
    """
    Endpoint for chat completions that mimics OpenAI's API structure.
    """
    group, api_key, user_info = await check(raw_request)
    llm_params = request.model_dump(exclude={"messages"}, exclude_none=True)
    connection, llm_params["model"] = resolve_connection_and_model(
        env.config, llm_params.get("model", "default_model")
    )
    ctx = RequestContext(
        request=request,
        http_request=raw_request,
        api_key_id=api_key_id(api_key),
        group=group if isinstance(group, str) else None,
        remote_addr=get_client_ip(raw_request),
        connection=connection,
        model=llm_params["model"],
        user_info=user_info,
    )
    logging.debug(
        "Resolved routing for [%s] --> connection: %s, model: %s",
        request.model,
        connection,
        llm_params["model"],
    )

    if not env.config.groups[group].allows_connecting_to(connection):
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "message": f"Your API key does not allow using the '{connection}' connection.",
                    "type": "invalid_request_error",
                    "param": None,
                    "code": "connection_not_allowed",
                }
            },
        )

    async_llm_func = env.connections[connection]
    logging.info("Querying LLM... params: %s", llm_params)

    if request.stream:
        stream_complete = asyncio.Event()
        middleware_task: asyncio.Task | None = None

        async def await_stream():
            await stream_complete.wait()

        async def on_stream_complete():
            stream_complete.set()
            if middleware_task:
                await middleware_task
            await log_non_blocking(ctx)  # After middleware

        if env.middleware:
            middleware_task = asyncio.create_task(
                run_middleware_chain(env.middleware, ctx, await_stream)
            )
            await asyncio.sleep(0)
            if middleware_task.done():
                middleware_task.result()

        return StreamingResponse(
            process_stream(
                async_llm_func, request, llm_params, ctx,
                on_complete=on_stream_complete,
            ),
            media_type="text/event-stream",
        )

    # Non-streaming
    async def execute_llm():
        ctx.response = await async_llm_func(request.messages, **llm_params)
        logging.info("LLM response: %s", ctx.response)

    try:
        await run_middleware_chain(env.middleware, ctx, execute_llm)
    except Exception as e:
        ctx.error = e
        raise
    finally:
        await log_non_blocking(ctx)  # Always log, after middleware

    return JSONResponse(
        {
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": str(ctx.response)},
                    "finish_reason": "stop",
                }
            ]
        }
    )

async def log(request_ctx: RequestContext):
    """
    Creates log records for current request using all configured log handlers.
    """
    if request_ctx.duration is None and request_ctx.created_at:
        request_ctx.duration = (datetime.now() - request_ctx.created_at).total_seconds()
    for handler in env.loggers:
        # check if it is async, then run both sync and async loggers in non-blocking way (sync too)
        if asyncio.iscoroutinefunction(handler):
            asyncio.create_task(handler(request_ctx))
        else:
            try:
                handler(request_ctx)
            except Exception as e:
                logging.error("Error in logger handler: %s", e)
                raise e


async def log_non_blocking(
    request_ctx: RequestContext,
) -> Optional[asyncio.Task]:
    """
    Non-blocking log function that schedules logging as an asynchronous task.
    """
    if env.loggers:
        task = asyncio.create_task(log(request_ctx))
        return task
