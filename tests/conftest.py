import sys
import pytest
import subprocess
import time
import signal
from pathlib import Path
from dataclasses import dataclass
from typing import Any
@dataclass
class ServerFixture:
    port: int
    process: any
    process: Any
    api_key: str


@pytest.fixture(scope="session")
def server_config_fn():
    """Fixture that starts the LM-Proxy server for testing and stops it after tests complete."""
    test_config_path = Path("tests/configs/config_fn.py")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "lm_proxy.app", "--config", str(test_config_path)],
    )
    time.sleep(2)
    from tests.configs.config_fn import config
    yield ServerFixture(
        port=config.port,
        process=server_process,
        model_name="any-model",
        api_key="py-test",
    )
    server_process.send_signal(signal.SIGTERM)
    server_process.wait()
