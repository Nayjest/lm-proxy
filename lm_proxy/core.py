import asyncio
import fnmatch
import json
import logging
import secrets
import time
import hashlib
from typing import List, Optional

import microcore as mc
from fastapi import HTTPException
from lm_proxy.loggers import LogEntry
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from .bootstrap import env
from .config import Config, Group
from .loggers import log_non_blocking
from .utils import get_client_ip


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
    async_llm_func, request: ChatCompletionRequest, llm_params, log_entry: LogEntry
):
    prompt = request.messages
    queue = asyncio.Queue()
    stream_id = f"chatcmpl-{secrets.token_hex(12)}"
    created = int(time.time())

    async def callback(chunk):
        await queue.put(chunk)

    def make_chunk(delta=None, content=None, finish_reason=None, error=None) -> str:
        if delta is None:
            delta = dict(content=str(content)) if content is not None else dict()
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
        # Initial chunk: role
        yield make_chunk(delta={"role": "assistant"})

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
            result = await task
            log_entry.response = result
        except Exception as e:
            log_entry.error = e
            yield make_chunk(error={"message": str(e), "type": type(e).__name__})

    # Final chunk: finish_reason
    yield make_chunk(finish_reason="stop")
    yield "data: [DONE]\n\n"
    await log_non_blocking(log_entry)


def read_api_key(request: Request) -> str:
    """
    Extracts the Bearer token from the Authorization header.
    returns '' if not present.
    """
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def check_api_key(api_key: Optional[str]) -> Optional[str]:
    """
    Validates an Client API key against configured groups and returns the matching group name.

    Args:
        api_key (Optional[str]): The Virtual / Client API key to validate.
    Returns:
        Optional[Group]: The Group object if the API key is valid and found in a group,
        None otherwise.
    """
    for group_name, group in env.config.groups.items():
        if api_key in group.api_keys:
            return group_name
    return None


def api_key_id(api_key: Optional[str]) -> str | None:
    if not api_key:
        return None
    return hashlib.md5(
        (api_key + env.config.encryption_key).encode("utf-8")
    ).hexdigest()


async def check(request: Request) -> tuple[str, str]:
    """
    API key and service availability check for endpoints.
    Args:
        request (Request): The incoming HTTP request object.
    Returns:
        tuple[str, str]: A tuple containing the group name and the API key.
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
    group: str | bool | None = (env.config.check_api_key)(api_key)
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
    return group, api_key


async def chat_completions(
    request: ChatCompletionRequest, raw_request: Request
) -> Response:
    """
    Endpoint for chat completions that mimics OpenAI's API structure.
    Streams the response from the LLM using microcore.
    """
    group, api_key = await check(raw_request)
    llm_params = request.model_dump(exclude={"messages"}, exclude_none=True)
    connection, llm_params["model"] = resolve_connection_and_model(
        env.config, llm_params.get("model", "default_model")
    )
    log_entry = LogEntry(
        request=request,
        api_key_id=api_key_id(api_key),
        group=group if isinstance(group, str) else None,
        remote_addr=get_client_ip(raw_request),
        connection=connection,
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
        return StreamingResponse(
            process_stream(async_llm_func, request, llm_params, log_entry),
            media_type="text/event-stream",
        )

    try:
        out = await async_llm_func(request.messages, **llm_params)
        log_entry.response = out
        logging.info("LLM response: %s", out)
    except Exception as e:
        log_entry.error = e
        await log_non_blocking(log_entry)
        raise
    await log_non_blocking(log_entry)

    return JSONResponse(
        {
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": str(out)},
                    "finish_reason": "stop",
                }
            ]
        }
    )
