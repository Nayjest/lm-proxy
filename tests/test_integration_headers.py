"""
Integration tests for extra headers functionality.
See tests/configs/extra_headers.yml
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest
import requests

from tests.conftest import start_proxy, stop_proxy


class HeaderCapturingHandler(BaseHTTPRequestHandler):
    captured = {}

    def do_POST(self):
        HeaderCapturingHandler.captured = dict(self.headers)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "choices": [{"message": {"role": "assistant", "content": "ok"}}],
            "model": "test"
        }).encode())

    def log_message(self, *_): pass


@pytest.fixture(scope="session")
def mock_server():
    server = HTTPServer(("127.0.0.1", 8131), HeaderCapturingHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    yield HeaderCapturingHandler
    server.shutdown()


@pytest.fixture(scope="session")
def proxy(mock_server):
    proc = start_proxy("tests/configs/extra_headers.yml", 8132)
    yield
    stop_proxy(proc)


def test_extra_headers_from_config(proxy, mock_server):
    response = requests.post(
        "http://127.0.0.1:8132/v1/chat/completions",
        json={"model": "test-model", "messages": [{"role": "user", "content": "test"}]},
        headers={"Authorization": "Bearer extra-headers-test"},
        timeout=30,
    )
    assert response.status_code == 200

    h = mock_server.captured
    assert h["X-Custom-Header"] == "custom-value"
    assert h["X-Another-Header"] == "another-value"
    assert h["X-Test-Id"] == "test-123"
    assert "dummy-key" in h.get("Authorization", "")


def test_extra_headers_forwarder(proxy, mock_server):
    response = requests.post(
        "http://127.0.0.1:8132/v1/chat/completions",
        json={"model": "test-model", "messages": [{"role": "user", "content": "test"}]},
        headers={
            "Authorization": "Bearer extra-headers-test",
            "dyn-forwarded-header": "some-value",
            "etag": "should-not-be-forwarded",
        },
        timeout=30,
    )
    assert response.status_code == 200

    h = mock_server.captured
    # headers from config
    assert h["X-Custom-Header"] == "custom-value"
    assert h["X-Another-Header"] == "another-value"
    assert h["X-Test-Id"] == "test-123"
    # auth
    assert "dummy-key" in h.get("Authorization", "")
    # forwarded header
    assert h["dyn-forwarded-header"] == "some-value"
    # not forwarded header
    assert "etag" not in h
