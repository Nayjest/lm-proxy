"""
Integration tests for extra headers functionality with real HTTP server.
See tests/configs/extra_headers.yml
"""

import sys
import json
import time
import signal
import pytest
import requests
import subprocess
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler


class HeaderCapturingHandler(BaseHTTPRequestHandler):
    """Minimal HTTP server that captures headers and returns OpenAI-compatible response."""

    captured_headers = {}

    def do_POST(self):
        HeaderCapturingHandler.captured_headers = dict(self.headers)
        response = {
            "choices": [{"message": {"role": "assistant", "content": "ok"}}],
            "model": "test"
        }
        body = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class MockLLMServer:
    """Context manager for running a mock LLM server."""

    def __init__(self, port=8124):
        self.port = port
        self.server = None

    def __enter__(self):
        self.server = HTTPServer(("127.0.0.1", self.port), HeaderCapturingHandler)
        Thread(target=self.server.serve_forever, daemon=True).start()
        time.sleep(0.5)
        return self

    def __exit__(self, *args):
        if self.server:
            self.server.shutdown()

    @property
    def headers(self):
        return HeaderCapturingHandler.captured_headers

    def reset(self):
        HeaderCapturingHandler.captured_headers = {}


@pytest.fixture
def mock_llm_server():
    with MockLLMServer() as server:
        yield server


@pytest.fixture
def lm_proxy_with_extra_headers(mock_llm_server):
    process = subprocess.Popen(
        [sys.executable, "-m", "lm_proxy.app", "--config", "tests/configs/extra_headers.yml"]
    )
    time.sleep(3)
    yield {"port": 8125, "api_key": "extra-headers-test", "model": "test-model"}
    process.send_signal(signal.SIGTERM)
    process.wait()


def make_request(port, api_key, model, message="test"):
    """Helper to make a request through lm-proxy."""
    return requests.post(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        json={"model": model, "messages": [{"role": "user", "content": message}]},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )


def test_extra_headers_forwarded_to_upstream(lm_proxy_with_extra_headers, mock_llm_server):
    """Test that extra headers configured in lm-proxy are forwarded to upstream server."""
    mock_llm_server.reset()
    cfg = lm_proxy_with_extra_headers

    response = make_request(cfg["port"], cfg["api_key"], cfg["model"])
    assert response.status_code == 200

    headers = mock_llm_server.headers
    assert headers["X-Custom-Header"] == "custom-value"
    assert headers["X-Another-Header"] == "another-value"
    assert headers["X-Test-Id"] == "test-123"


def test_headers_consistent_across_requests(lm_proxy_with_extra_headers, mock_llm_server):
    """Test that headers are consistently forwarded across multiple requests."""
    cfg = lm_proxy_with_extra_headers

    for i in range(2):
        mock_llm_server.reset()
        assert make_request(cfg["port"], cfg["api_key"], cfg["model"]).status_code == 200
        headers = mock_llm_server.headers
        assert headers["X-Custom-Header"] == "custom-value"
        assert headers["X-Another-Header"] == "another-value"
        assert headers["X-Test-Id"] == "test-123"


def test_authorization_uses_upstream_credentials(lm_proxy_with_extra_headers, mock_llm_server):
    """Test that Authorization uses upstream credentials, not client credentials."""
    mock_llm_server.reset()
    cfg = lm_proxy_with_extra_headers

    assert make_request(cfg["port"], cfg["api_key"], cfg["model"]).status_code == 200

    if "Authorization" in mock_llm_server.headers:
        assert "dummy-key" in mock_llm_server.headers["Authorization"]
