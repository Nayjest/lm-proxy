import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
sys.path.append(str(root))

from lm_proxy.config import Config, Group

def check_api_key(api_key: str) -> str:
    return "default" if api_key == "py-test" else False

import microcore as mc
mc.configure(
    DOT_ENV_FILE=".env",
)

config = Config(
    port=8123,
    host="127.0.0.1",
    check_api_key=check_api_key,
    connections={
        "py_oai": mc.env().llm_async_function
    },
    routing={
        "*": "py_oai.gpt-3.5-turbo",
    },
    groups={
        "default": Group(connections="*")
    }
)