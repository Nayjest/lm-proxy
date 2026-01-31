"""
Integration tests for extra headers functionality.
See tests/configs/extra_headers.yml
"""

import json
import signal
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


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


def wait_for_server(url, timeout=10):
    session = requests.Session()
    session.mount("http://", HTTPAdapter(max_retries=Retry(total=20, backoff_factor=0.1)))
    session.get(url, timeout=timeout)


@pytest.fixture(scope="module")
def mock_server():
    server = HTTPServer(("127.0.0.1", 8124), HeaderCapturingHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    yield HeaderCapturingHandler
    server.shutdown()


@pytest.fixture(scope="module")
def proxy(mock_server):
    proc = subprocess.Popen(
        [sys.executable, "-m", "lm_proxy.app", "--config", "tests/configs/extra_headers.yml"]
    )
    wait_for_server("http://127.0.0.1:8125/health")  # assumes health endpoint exists
    yield
    proc.send_signal(signal.SIGTERM)
    proc.wait()


@pytest.fixture(autouse=True)
def reset_captured(mock_server):
    mock_server.captured = {}


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
    assert chat().status_code == 200
    assert_extra_headers(mock_server.captured)


def test_headers_consistent_across_requests(proxy, mock_server):
    for _ in range(2):
        mock_server.captured = {}
        assert chat().status_code == 200
        assert_extra_headers(mock_server.captured)


def test_uses_upstream_credentials(proxy, mock_server):
    assert chat().status_code == 200
    assert "dummy-key" in mock_server.captured.get("Authorization", "")