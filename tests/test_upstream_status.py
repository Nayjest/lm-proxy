import httpx
import openai
import pytest
import requests
from starlette.requests import Request

from lm_proxy.base_types import ChatCompletionRequest
from lm_proxy.bootstrap import bootstrap
from lm_proxy.config import Config
from lm_proxy.core import chat_completions
from lm_proxy.errors import OpenAIHTTPException
from tests.conftest import ServerFixture


class ProviderError(Exception):
    def __init__(self, **attrs):
        self.__dict__.update(attrs)


def openai_error(status: int) -> openai.APIStatusError:
    response = httpx.Response(status, request=httpx.Request("POST", "http://upstream"))
    return openai.APIStatusError("refused", response=response, body=None)


@pytest.mark.parametrize(
    "error, status",
    [
        (openai_error(429), 429),
        (openai_error(402), 402),
        (ProviderError(code=400), 400),  # Google
        (ProviderError(response=httpx.Response(503)), 503),  # httpx, requests
        (ProviderError(status_code=200, code="rate_limit_exceeded"), 502),
        (openai.APIConnectionError(request=httpx.Request("POST", "http://upstream")), 502),
        (RuntimeError("no status"), 502),
    ],
)
@pytest.mark.parametrize("stream", [False, True])
async def test_upstream_status_is_passed_through(error, status, stream):
    async def failing_connection(*_args, **_kwargs):
        raise error

    bootstrap(
        Config(
            connections={"upstream": failing_connection},
            routing={"*": "upstream.*"},
            api_key_check=lambda api_key: "default",
        ),
        debug=False,
    )
    request = ChatCompletionRequest(
        model="any", messages=[{"role": "user", "content": "Hi"}], stream=stream
    )
    with pytest.raises(OpenAIHTTPException) as exc_info:
        await chat_completions(request, Request(scope={"type": "http", "headers": []}))
    assert exc_info.value.status_code == status


@pytest.mark.parametrize("stream", [False, True])
def test_provider_rejection_keeps_its_status(server_config_fn: ServerFixture, stream):
    """The provider refuses a request without messages."""
    cfg = server_config_fn
    response = requests.post(
        f"http://127.0.0.1:{cfg.port}/v1/chat/completions",
        json={"model": cfg.model, "messages": [], "stream": stream},
        headers={"Authorization": f"Bearer {cfg.api_key}"},
        timeout=120,
    )
    assert response.status_code == 400
    assert response.json()["error"]["type"] == "upstream_error"
