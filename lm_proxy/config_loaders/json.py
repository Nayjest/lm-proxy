"""JSON configuration loader."""

import json


def load_json_config(config_path: str) -> dict:
    """Loads configuration from a JSON file."""
    # utf-8-sig skips the byte order mark that Windows text editors may add,
    # the JSON parser rejects it
    with open(config_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)
