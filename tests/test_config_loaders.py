import os
from pathlib import Path

import dotenv
import pytest

from lm_proxy.config import Config


def test_config_loaders():
    root = Path(__file__).resolve().parent
    dotenv.load_dotenv(root.parent / ".env.template", override=True)
    oai_key = os.getenv("OPENAI_API_KEY")
    toml = Config.load(root / "configs" / "test_config.toml")
    json = Config.load(root / "configs" / "test_config.json")
    yaml = Config.load(root / "configs" / "test_config.yml")

    assert json.model_dump() == yaml.model_dump() == toml.model_dump()
    assert json.connections["test_openai"]["api_key"] == oai_key

    py = Config.load(root / "configs" / "config_fn.py")

    # Expect an error for unsupported format
    with pytest.raises(ValueError):
        Config.load(root / "configs" / "test_config.xyz")
