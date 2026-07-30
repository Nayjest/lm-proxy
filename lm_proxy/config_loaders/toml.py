"""TOML configuration loader."""

import tomllib


def load_toml_config(config_path: str) -> dict:
    """Loads configuration from a TOML file."""
    # utf-8-sig skips the byte order mark that Windows text editors may add,
    # tomllib rejects it
    with open(config_path, "r", encoding="utf-8-sig") as f:
        return tomllib.loads(f.read())
