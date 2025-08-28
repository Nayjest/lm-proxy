import sys
from pathlib import Path
import microcore as mc

root = Path(__file__).resolve().parents[3]
sys.path.append(str(root))

from lm_proxy.config import Config, Group  # noqa


def check_api_key(api_key: str) -> str | None:
    return "default" if api_key == "py-test" else None


mc.configure(
    DOT_ENV_FILE=".env",
    EMBEDDING_DB_TYPE=mc.EmbeddingDbType.NONE,
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
