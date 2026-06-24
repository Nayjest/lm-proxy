import json

import microcore as mc

from lm_proxy.core import log_non_blocking
from lm_proxy.base_types import ChatCompletionRequest, RequestContext
from lm_proxy.config import Config
from lm_proxy.bootstrap import bootstrap
from lm_proxy.utils import CustomJsonEncoder


async def test_custom_config():

    logs = []
    bootstrap(
        Config(
            connections={},
            loggers=[
                {
                    "class": "lm_proxy.loggers.BaseLogger",
                    "log_writer": lambda data: logs.append(json.dumps(data, cls=CustomJsonEncoder)),
                }
            ],
        )
    )
    request = ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Test request message"}],
    )
    response = mc.LLMResponse("Test response message", dict(prompt=request.messages))
    task = await log_non_blocking(RequestContext(request=request, response=response))
    if task:
        await task
    assert len(logs) == 1
    log_data = json.loads(logs[0])
    assert log_data["request"]["model"] == "gpt-3.5-turbo"
    assert log_data["response"] == "Test response message"


async def test_json(tmp_path):
    bootstrap(
        Config(
            connections={},
            loggers=[
                {
                    "class": "lm_proxy.loggers.BaseLogger",
                    "log_writer": {
                        "class": "lm_proxy.loggers.JsonLogWriter",
                        "file_name": tmp_path / "json_log.log",
                    },
                }
            ],
        )
    )
    request = ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Test request message"}],
    )
    response = mc.LLMResponse("Test response message", dict(prompt=request.messages))
    task = await log_non_blocking(RequestContext(request=request, response=response))
    if task:
        await task
    task = await log_non_blocking(RequestContext(request=request, response=response))
    if task:
        await task
    with open(tmp_path / "json_log.log", "r") as f:
        lines = f.readlines()
        assert len(lines) == 2
        log_data = json.loads(lines[0])
        assert log_data["request"]["model"] == "gpt-3.5-turbo"
        assert log_data["response"] == "Test response message"


def test_json_writer_reuses_file_handle(tmp_path):
    """JsonLogWriter should keep one file handle open across multiple writes."""
    from lm_proxy.loggers import JsonLogWriter

    log_file = tmp_path / "reuse_test.log"
    writer = JsonLogWriter(file_name=str(log_file))

    # File handle should be open after construction
    assert not writer._file.closed

    writer({"event": "first"})
    writer({"event": "second"})

    # Handle remains open between writes
    assert not writer._file.closed

    # Explicit close works
    writer.close()
    assert writer._file.closed

    # Double-close is safe
    writer.close()

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "first"
    assert json.loads(lines[1])["event"] == "second"
