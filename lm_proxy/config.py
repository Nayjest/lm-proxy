"""
Configuration models for LM-Proxy settings.
This module defines Pydantic models that match the structure of config.toml.
"""
import os
import tomllib
from pydantic import BaseModel, Field


class Config(BaseModel):
    """Main configuration model matching config.toml structure."""
    host: str = "0.0.0.0"
    port: int = 8000
    connections: dict[str, dict]
    routing: dict[str, str] = Field(default_factory=dict)

    @staticmethod
    def load(config_path: str = "config.toml") -> "Config":
        """
        Load configuration from a TOML file.

        Args:
            config_path: Path to the config.toml file

        Returns:
            Config object with parsed configuration
        """

        with open(config_path, "rb") as f:
            config_data = tomllib.load(f)

        # Process environment variables in api_key fields
        for conn_name, conn_config in config_data.get("connections", {}).items():
            for key, value in conn_config.items():
                if isinstance(value, str) and value.startswith("env:"):
                    env_var = value.split(":", 1)[1]
                    conn_config[key] = os.environ.get(env_var, "")
        return Config(**config_data)
