"""Tests for the `print_stream` configuration option."""

import re

import microcore as mc

from lm_proxy.base_types import ChatCompletionRequest, RequestContext
from lm_proxy.bootstrap import bootstrap
from lm_proxy.config import Config
from lm_proxy.core import print_llm_request, process_stream


def remove_colors(text: str) -> str:
    return re.sub(r"\x1b\[\d+m", "", text)


def make_request(content: str = "Hi") -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": content}],
        stream=True,
    )


async def llm_hello(_prompt, callback=None, **_kwargs):
    for chunk in ("Hel", "lo"):
        # emulates how microcore LLM API functions notify configured callbacks
        for config_callback in mc.config().CALLBACKS:
            config_callback(chunk)
        await callback(chunk)
    return mc.LLMResponse("Hello")


async def test_stream_is_not_printed_by_default(capsys):
    bootstrap(Config(connections={}))
    request = make_request()
    async for _ in process_stream(llm_hello, request, RequestContext(request=request)):
        pass
    assert capsys.readouterr().out == ""


async def test_print_stream(capsys):
    mc.configure(USE_DOT_ENV=False, LLM_API_KEY="test", EMBEDDING_DB_TYPE=mc.EmbeddingDbType.NONE)
    bootstrap(Config(connections={}, print_stream=True))
    try:
        request = make_request()
        ctx = RequestContext(request=request, llm_params={"model": "gpt-3.5-turbo"})
        print_llm_request(ctx)
        chunks = [chunk async for chunk in process_stream(llm_hello, request, ctx)]
    finally:
        mc.config().CALLBACKS.clear()
        mc.env().llm_before_handlers.clear()
        mc.env().llm_after_handlers.clear()

    out = remove_colors(capsys.readouterr().out)
    # the request is printed
    assert "Requesting LLM gpt-3.5-turbo:" in out
    assert "[User]:" in out
    assert "Hi" in out
    # the response is printed as it is streamed
    assert "LLM Response:" in out
    assert "Hello" in out
    # the line of the streamed response is terminated
    assert out.endswith("\n")
    assert ctx.response == "Hello"
    assert chunks[-1] == "data: [DONE]\n\n"


async def test_long_prompt_is_printed_without_truncation(capsys):
    mc.configure(USE_DOT_ENV=False, LLM_API_KEY="test", EMBEDDING_DB_TYPE=mc.EmbeddingDbType.NONE)
    bootstrap(Config(connections={}, print_stream=True))
    prompt_lines = [f"line {i}" for i in range(100)]
    try:
        ctx = RequestContext(request=make_request("\n".join(prompt_lines)))
        print_llm_request(ctx)
    finally:
        mc.config().CALLBACKS.clear()
        mc.env().llm_before_handlers.clear()
        mc.env().llm_after_handlers.clear()

    out = remove_colors(capsys.readouterr().out)
    assert "(output was truncated)" not in out
    for line in prompt_lines:
        assert line in out
