import json

import microcore as mc

from lm_proxy.base_types import ChatCompletionRequest, RequestContext
from lm_proxy.bootstrap import bootstrap
from lm_proxy.config import Config
from lm_proxy.core import process_stream


async def llm_tool_call(_prompt, callback=None, **_kwargs):
    return mc.LLMResponse(
        "",
        tool_calls=[mc.ToolCall(name="ping", arguments='{"host": "a"}', id="call_1")],
        finish_reason="tool_calls",
    )


async def llm_text(_prompt, callback=None, **_kwargs):
    await callback("Hello")
    return mc.LLMResponse("Hello", finish_reason="length")


async def llm_plain_string(_prompt, callback=None, **_kwargs):
    await callback("Hello")
    return "Hello"


async def chunks(llm):
    bootstrap(Config(connections={}))
    request = ChatCompletionRequest(
        model="test", messages=[{"role": "user", "content": "Ping"}], stream=True
    )
    stream = await process_stream(llm, request, RequestContext(request=request))
    events = [e async for e in stream]
    assert events[-1] == "data: [DONE]\n\n"
    return [json.loads(e[6:])["choices"][0] for e in events[:-1]]


async def test_tool_calls_are_streamed():
    output = await chunks(llm_tool_call)
    assert [c["delta"]["tool_calls"] for c in output if "tool_calls" in c["delta"]] == [
        [
            {
                "index": 0,
                "id": "call_1",
                "type": "function",
                "function": {"name": "ping", "arguments": '{"host": "a"}'},
            }
        ]
    ]
    assert output[-1]["finish_reason"] == "tool_calls"


async def test_text_stream_reports_finish_reason():
    output = await chunks(llm_text)
    assert [c["delta"].get("content") for c in output].count("Hello") == 1
    assert not any("tool_calls" in c["delta"] for c in output)
    assert output[-1]["finish_reason"] == "length"


async def test_custom_connection_returning_plain_string():
    output = await chunks(llm_plain_string)
    assert output[-1]["finish_reason"] == "stop"
