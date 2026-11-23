import pytest
from lm_proxy.config import Config
from lm_proxy.core import resolve_connection_and_model
from lm_proxy.errors import OpenAIHTTPException


async def test_resolve_connection_and_model():
    c = Config(connections={"a": {}, "b": {}, "c": {}})
    with pytest.raises(OpenAIHTTPException, match="matched") as exc_info:
        resolve_connection_and_model(c, "model")
    assert (exc_info.value.status_code, exc_info.value.code) == (404, "model_not_found")
    c.routing = {
        "client-model": "a.provider-model",
    }
    assert resolve_connection_and_model(c, "client-model") == ("a", "provider-model")

    c.routing["gpt*"] = "c.model"
    assert resolve_connection_and_model(c, "gpt-8") == ("c", "model")

    c.routing["*"] = "b.*"
    assert resolve_connection_and_model(c, "client-model2") == ("b", "client-model2")
