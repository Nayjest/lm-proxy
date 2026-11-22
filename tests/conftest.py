import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import requests

import microcore as mc


@dataclass
class ServerFixture:
    port: int
    process: Any
    api_key: str
    model: str = field(default=None)


def wait_for_server(url, proc=None, timeout=30):
    """Wait for the server, failing at once if its process is already gone."""
    deadline = time.monotonic() + timeout
    while True:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError(f"proxy exited with code {proc.returncode} before serving {url}")
        try:
            requests.get(url, timeout=2)
            return
        except requests.RequestException:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.1)


def start_proxy(config_path: str, port: int):
    proc = subprocess.Popen([sys.executable, "-m", "lm_proxy", "--config", config_path])
    try:
        wait_for_server(f"http://127.0.0.1:{port}/health", proc)
    except Exception:
        proc.kill()
        raise
    return proc


def stop_proxy(proc):
    proc.send_signal(signal.SIGTERM)
    proc.wait()


@pytest.fixture(scope="session")
def server_config_fn():
    test_config_path = Path("tests/configs/config_fn.py")
    from tests.configs.config_fn import config

    proc = start_proxy(str(test_config_path), config.port)
    yield ServerFixture(
        port=config.port,
        process=proc,
        model="any-model",
        api_key="py-test",
    )
    stop_proxy(proc)


async def llm_ok_connection(*args, **kwargs):
    return mc.LLMResponse("ok")
