import json

import microcore as mc

from lm_proxy.core import ChatCompletionRequest
from lm_proxy.loggers import LogEntry
from lm_proxy.loggers.core import log_non_blocking
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
                    "log_writer": lambda data: logs.append(
                        json.dumps(data, cls=CustomJsonEncoder)
                    ),
                }
            ],
        )
    )
    request = ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Test request message"}],
    )
    response = mc.LLMResponse("Test response message", dict(prompt=request.messages))
    task = await log_non_blocking(LogEntry(request=request, response=response))
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
    task = await log_non_blocking(LogEntry(request=request, response=response))
    if task:
        await task
    task = await log_non_blocking(LogEntry(request=request, response=response))
    if task:
        await task
    with open(tmp_path / "json_log.log", "r") as f:
        lines = f.readlines()
        assert len(lines) == 2
        log_data = json.loads(lines[0])
        assert log_data["request"]["model"] == "gpt-3.5-turbo"
        assert log_data["response"] == "Test response message"
