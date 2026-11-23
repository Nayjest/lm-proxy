"""
Logging of the token usage reported by the provider.
See tests/configs/usage_logging.yml
"""

import json
import time
from pathlib import Path

import pytest
import requests

from tests.conftest import start_proxy, stop_proxy

LOG_FILE = Path("storage/usage_logging_test.log")


@pytest.fixture(scope="module")
def proxy():
    LOG_FILE.unlink(missing_ok=True)
    proc = start_proxy("tests/configs/usage_logging.yml", 8134)
    yield
    stop_proxy(proc)


def test_cached_tokens_are_logged(proxy):
    for stream in (False, True):
        response = requests.post(
            "http://127.0.0.1:8134/v1/chat/completions",
            json={
                "model": "any-model",
                "messages": [{"role": "user", "content": "Say hi"}],
                "stream": stream,
            },
            headers={"Authorization": "Bearer usage-logging-test"},
            timeout=120,
        )
        assert response.status_code == 200
    time.sleep(1)  # the logger is non-blocking
    entries = [json.loads(line) for line in LOG_FILE.read_text().splitlines()]
    assert len(entries) == 2
    for entry in entries:
        assert entry["prompt_tokens"] > 0
        assert entry["cached_tokens"] >= 0
