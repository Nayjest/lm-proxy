"""JSON configuration loader."""

import json


def load_json_config(config_path: str) -> dict:
    """Loads configuration from a JSON file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)
