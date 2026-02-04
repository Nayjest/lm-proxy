import pytest

import microcore as mc
from starlette.requests import Request
from fastapi import HTTPException

from lm_proxy.base_types import ChatCompletionRequest
from lm_proxy.bootstrap import bootstrap
from lm_proxy.config import Config
from lm_proxy.core import check, chat_completions


async def test_disabled():
    bootstrap(Config(enabled=False, connections={}))
    with pytest.raises(HTTPException, match="disabled"):
        await chat_completions(
            ChatCompletionRequest(model='model', messages=[mc.UserMsg('Hello')]),
            Request(scope={"type": "http", "headers": []})
        )


async def test_403():
    bootstrap(Config(connections={}))
    with pytest.raises(HTTPException) as excinfo:
        await check(Request(scope={
            "type": "http",
            "headers": [
                (b"authorization", b"Bearer mykey"),
            ],
        }))
    assert excinfo.value.status_code == 403
    assert "Incorrect API key" in str(excinfo.value)
