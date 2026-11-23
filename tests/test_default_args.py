"""
Default request parameters of a connection.
See tests/configs/default_args.yml
"""

import json

import pytest
import requests

from tests.conftest import start_proxy, stop_proxy


@pytest.fixture(scope="module")
def proxy():
    proc = start_proxy("tests/configs/default_args.yml", 8133)
    yield
    stop_proxy(proc)


def test_default_args_reach_the_provider(proxy):
    response = requests.post(
        "http://127.0.0.1:8133/v1/chat/completions",
        json={
            "model": "any-model",
            "messages": [{"role": "user", "content": "What is the capital of France?"}],
        },
        headers={"Authorization": "Bearer default-args-test"},
        timeout=120,
    )
    assert response.status_code == 200
    answer = json.loads(response.json()["choices"][0]["message"]["content"])
    assert "paris" in answer["capital"].lower()
