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

    assert json.model_dump() == toml.model_dump()
    assert json.model_dump() == yaml.model_dump()

    assert json.connections["test_openai"]["api_key"] == oai_key

    py = Config.load(root / "configs" / "config_fn.py")
    assert isinstance(py, Config)

    # Expect an error for unsupported format
    with pytest.raises(ValueError):
        Config.load(root / "configs" / "test_config.xyz")


def test_config_loaders_ignore_byte_order_mark(tmp_path):
    """Configuration files saved by Windows text editors may start with a UTF-8 BOM."""
    root = Path(__file__).resolve().parent
    dotenv.load_dotenv(root.parent / ".env.template", override=True)
    expected = Config.load(root / "configs" / "test_config.toml").model_dump()

    for file_name in ("test_config.toml", "test_config.json", "test_config.yml"):
        config_path = tmp_path / file_name
        config_path.write_bytes(b"\xef\xbb\xbf" + (root / "configs" / file_name).read_bytes())
        assert Config.load(config_path).model_dump() == expected, file_name
