"""
Integration tests for extra headers functionality.
See tests/configs/extra_headers.yml
"""

import json
import signal
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest
import requests


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


@pytest.fixture
def mock_server():
    server = HTTPServer(("127.0.0.1", 8124), HeaderCapturingHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.5)
    yield HeaderCapturingHandler
    server.shutdown()


@pytest.fixture
def proxy(mock_server):
    proc = subprocess.Popen(
        [sys.executable, "-m", "lm_proxy.app", "--config", "tests/configs/extra_headers.yml"]
    )
    time.sleep(3)
    yield
    proc.send_signal(signal.SIGTERM)
    proc.wait()


def chat(msg="test"):
    return requests.post(
        "http://127.0.0.1:8125/v1/chat/completions",
        json={"model": "test-model", "messages": [{"role": "user", "content": msg}]},
        headers={"Authorization": "Bearer extra-headers-test"},
        timeout=30,
    )


def assert_extra_headers(headers):
    assert headers["X-Custom-Header"] == "custom-value"
    assert headers["X-Another-Header"] == "another-value"
    assert headers["X-Test-Id"] == "test-123"


def test_extra_headers_forwarded(proxy, mock_server):
    mock_server.captured = {}
    assert chat().status_code == 200
    assert_extra_headers(mock_server.captured)


def test_headers_consistent_across_requests(proxy, mock_server):
    for _ in range(2):
        mock_server.captured = {}
        assert chat().status_code == 200
        assert_extra_headers(mock_server.captured)


def test_uses_upstream_credentials(proxy, mock_server):
    mock_server.captured = {}
    assert chat().status_code == 200
    assert "dummy-key" in mock_server.captured.get("Authorization", "")
