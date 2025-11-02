import pytest
from lm_proxy.config import Config
from lm_proxy.core import resolve_connection_and_model


async def test_resolve_connection_and_model():
    c = Config(connections={"a": {}, "b": {}, "c": {}})
    with pytest.raises(ValueError, match="matched"):
        resolve_connection_and_model(c, "model")
    c.routing = {
        "client-model": "a.provider-model",
    }
    assert resolve_connection_and_model(c, "client-model") == ("a", "provider-model")

    c.routing["gpt*"] = "c.model"
    assert resolve_connection_and_model(c, "gpt-8") == ("c", "model")

    c.routing["*"] = "b.*"
    assert resolve_connection_and_model(c, "client-model2") == ("b", "client-model2")
