"""
Integration tests for rate limiter handler.
See tests/configs/rate_limiter.yml
"""

import time

import pytest
import requests

from tests.conftest import start_proxy, stop_proxy


@pytest.fixture(scope="function")
def proxy():
    proc = start_proxy("tests/configs/rate_limiter.yml", 8126)
    yield
    stop_proxy(proc)

def make_request(content = "test", api_key="rate-limiter-test") -> requests.Response:
    return requests.post(
        "http://127.0.0.1:8126/v1/chat/completions",
        json={"model": "test-model", "messages": [{"role": "user", "content": content}]},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )

def test_rate_limiter_blocks_over_limit(proxy):
    """Test that requests exceeding rate limit are blocked with 429."""
    # Make 2 successful requests
    for i in range(2):
        response = make_request(f"test {i+1}")
        assert response.status_code == 200

    response = make_request(f"test second key", api_key="key2")
    assert response.status_code == 200

    # 3rd and 4th requests with same key using first API key should be blocked
    for i in range(2):
        response = make_request(f"test {i+1+2}")
        assert response.status_code == 429
        assert "Retry-After" in response.headers

        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "rate_limit_error"
        assert data["error"]["code"] == "rate_limit_exceeded"
        assert "Rate limit exceeded" in data["error"]["message"]

    time.sleep(2 + 0.01)  # wait for rate limit window to expire
    response = make_request()
    assert response.status_code == 200
    # 5th request to connection should be blocked if not count previously blocked
    response = make_request()
    assert response.status_code == 429
