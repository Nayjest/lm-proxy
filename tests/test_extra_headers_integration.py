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


@pytest.fixture(scope="module")
def mock_server():
    server = HTTPServer(("127.0.0.1", 8124), HeaderCapturingHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    yield HeaderCapturingHandler
    server.shutdown()


@pytest.fixture(scope="module")
def proxy(mock_server):
    proc = start_proxy("tests/configs/extra_headers.yml", 8125)
    yield
    stop_proxy(proc)


def test_extra_headers_forwarded(proxy, mock_server):
    response = requests.post(
        "http://127.0.0.1:8125/v1/chat/completions",
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
