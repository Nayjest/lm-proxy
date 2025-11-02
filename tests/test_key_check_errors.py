import pytest

from starlette.requests import Request
from fastapi import HTTPException

from lm_proxy.bootstrap import bootstrap
from lm_proxy.config import Config
from lm_proxy.core import check


async def test_disabled():
    bootstrap(Config(enabled=False, connections={}))
    with pytest.raises(HTTPException, match="disabled"):
        await check(Request(scope={
            "type": "http",
            "headers": [],
        }))


async def test_403():
    bootstrap(Config(connections={}))
    with pytest.raises(HTTPException, match="Incorrect API key"):
        await check(Request(scope={
            "type": "http",
            "headers": [
                (b"authorization", b"Bearer mykey"),
            ],
        }))
