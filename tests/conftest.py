import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import microcore as mc


@dataclass
class ServerFixture:
    port: int
    process: Any
    api_key: str
    model: str = field(default=None)


def wait_for_server(url, timeout=26):
    session = requests.Session()
    session.mount("http://", HTTPAdapter(max_retries=Retry(total=10, backoff_factor=0.1)))
    session.get(url, timeout=timeout)


def start_proxy(config_path: str, port: int):
    proc = subprocess.Popen([sys.executable, "-m", "lm_proxy", "--config", config_path])
    time.sleep(2)
    wait_for_server(f"http://127.0.0.1:{port}/health")
    return proc


def stop_proxy(proc):
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)



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
