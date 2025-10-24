import json

from starlette.requests import Request

from lm_proxy.config import Config, ModelListingMode
from lm_proxy.bootstrap import bootstrap, env
from lm_proxy.models_endpoint import models


async def test_models_endpoint():
    async def dummy_inference(prompt):
        return "dummy response"

    bootstrap(
        Config(
            connections={
                "A": dummy_inference,
                "B": dummy_inference,
            },
            routing={
                "a": "A.a",
                "b": "B.b",
                "my-gpt-*": "B.*",
                "*": "A.*",
            },
            model_listing_mode=ModelListingMode.AS_IS,
            groups={
                "default": dict(
                    connections=["A", "B"],
                    api_keys=["testkey"],
                ),
                "only_b": dict(
                    connections=["B"],
                    api_keys=["bkey"],
                ),
            },
        )
    )

    req = Request(
        dict(
            type="http",
            headers=[(b"authorization", b"Bearer testkey")],
        )
    )

    payload = json.loads((await models(req)).body.decode())

    assert isinstance(payload, dict)
    assert "data" in payload
    assert isinstance(payload["data"], list)
    assert len(payload["data"]) == 4
    env.config.model_listing_mode = ModelListingMode.IGNORE_WILDCARDS
    payload = json.loads((await models(req)).body.decode())
    assert len(payload["data"]) == 2  # Only 'a' and 'b'
    assert payload["data"][0]["id"] in ("a", "b")
    assert payload["data"][1]["id"] in ("a", "b")
