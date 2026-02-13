from pathlib import Path

from starlette.requests import Request

from lm_proxy.bootstrap import bootstrap
from lm_proxy.core import check
from lm_proxy.api_key_check import AllowAll


async def test_allow_all():
    root = Path(__file__).resolve().parent
    bootstrap(root / "configs" / "no_api_key_check.yml")
    assert await check(
        Request(
            scope={
                "type": "http",
                "headers": [],
            }
        )
    ) == ("default", "", {"api_key": ""})

    # Test with key
    assert await check(
        Request(
            scope={
                "type": "http",
                "headers": [(b"authorization", b"Bearer 11")],
            }
        )
    ) == ("default", "11", {"api_key": "11"})

    assert AllowAll()("") == ("default", {"api_key": ""})
    assert AllowAll(capture_api_key=False)("") == ("default", {})
