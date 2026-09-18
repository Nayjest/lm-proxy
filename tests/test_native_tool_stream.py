import json

import microcore as mc

from lm_proxy.base_types import ChatCompletionRequest, RequestContext
from lm_proxy.bootstrap import bootstrap
from lm_proxy.config import Config
from lm_proxy.core import process_stream


def native_chunk(delta=None, finish_reason=None, choices=True):
    return {
        "object": "chat.completion.chunk",
        "choices": (
            []
            if not choices
            else [
                {"index": 0, "delta": delta or {}, "finish_reason": finish_reason}
            ]
        ),
    }


async def llm_tool_call(_prompt, callback=None, **_kwargs):
    await callback.on_openai_chunk(
        native_chunk(
            {
                "tool_calls": [
                    {"index": 0, "function": {"name": "ping", "arguments": "{"}}
                ]
            }
        )
    )
    await callback.on_openai_chunk(
        native_chunk(
            {"tool_calls": [{"index": 0, "function": {"arguments": "}"}}]},
            "tool_calls",
        )
    )
    await callback.on_openai_chunk(native_chunk(choices=False))
    await callback("ignored")
    return mc.LLMResponse("")


async def llm_text(_prompt, callback=None):
    await callback.on_openai_chunk(native_chunk({"content": "Hello"}))
    await callback("Hello")
    await callback.on_openai_chunk(native_chunk(finish_reason="stop"))
    return mc.LLMResponse("Hello")


async def events(llm):
    bootstrap(Config(connections={}))
    request = ChatCompletionRequest(
        model="test", messages=[{"role": "user", "content": "Ping"}], stream=True
    )
    return [
        event async for event in process_stream(llm, request, RequestContext(request=request))
    ]


def chunks(events):
    return [
        json.loads(event[6:]) for event in events if event.startswith("data: {")
    ]


async def test_native_tool_call_stream_is_preserved():
    output = await events(llm_tool_call)
    tool_chunks = [
        chunk
        for chunk in chunks(output)
        if "tool_calls" in chunk["choices"][0]["delta"]
    ]

    assert len(tool_chunks) == 2
    assert (
        tool_chunks[0]["choices"][0]["delta"]["tool_calls"][0]["function"]["name"]
        == "ping"
    )
    assert (
        tool_chunks[1]["choices"][0]["delta"]["tool_calls"][0]["function"]["arguments"]
        == "}"
    )
    assert tool_chunks[-1]["id"] == tool_chunks[0]["id"]
    assert chunks(output)[-1]["choices"][0]["finish_reason"] == "tool_calls"
    assert output[-1] == "data: [DONE]\n\n"


async def test_native_text_chunks_are_not_duplicated():
    output = await events(llm_text)
    content = [chunk["choices"][0]["delta"].get("content") for chunk in chunks(output)]

    assert content.count("Hello") == 1
    assert chunks(output)[-1]["choices"][0]["finish_reason"] == "stop"
