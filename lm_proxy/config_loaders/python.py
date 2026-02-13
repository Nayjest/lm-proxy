"""Loader for Python configuration files."""

import importlib.util
from ..config import Config


def load_python_config(config_path: str) -> Config:
    """Load configuration from a Python file."""
    spec = importlib.util.spec_from_file_location("config_module", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    return config_module.config
