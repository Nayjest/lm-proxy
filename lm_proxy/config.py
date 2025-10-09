"""
Configuration models for LM-Proxy settings.
This module defines Pydantic models that match the structure of config.toml.
"""

import os
from typing import Union, Callable
import tomllib
import importlib.util

from pydantic import BaseModel, Field, ConfigDict
from microcore.utils import resolve_callable

from .utils import resolve_instance_or_callable


class Group(BaseModel):
    api_keys: list[str] = Field(default_factory=list)
    allowed_connections: str = Field(default="*")  # Comma-separated list or "*"

    def allows_connecting_to(self, connection_name: str) -> bool:
        """Check if the group allows access to the specified connection."""
        if self.allowed_connections == "*":
            return True
        return connection_name in self.allowed_connections


class Config(BaseModel):
    """Main configuration model matching config.toml structure."""

    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    dev_autoreload: bool = False
    connections: dict[str, Union[dict, Callable]] = Field(
        ...,  # Required field (no default)
        description="Dictionary of connection configurations",
        examples=[{"openai": {"api_key": "sk-..."}}],
    )
    routing: dict[str, str] = Field(default_factory=dict)
    """ model_name_pattern* => connection_name.< model | * >, example: {"gpt-*": "oai.*"} """
    groups: dict[str, Group] = Field(default_factory=dict)
    check_api_key: Union[str, Callable] = Field(default="lm_proxy.core.check_api_key")
    loggers: list[Union[str, Callable, dict]] = Field(default_factory=list)
    encription_key: str = Field(
        default="Eclipse", description="Key for encrypting sensitive data"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.check_api_key = resolve_callable(self.check_api_key)
        self.loggers = [resolve_instance_or_callable(logger) for logger in self.loggers]
        if not self.groups:
            # Default group with no restrictions
            self.groups = {"default": Group()}

    @staticmethod
    def load(config_path: str = "config.toml") -> "Config":
        """
        Load configuration from a TOML file.

        Args:
            config_path: Path to the config.toml file

        Returns:
            Config object with parsed configuration
        """
        if config_path.endswith(".py"):
            spec = importlib.util.spec_from_file_location("config_module", config_path)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            return config_module.config
        elif config_path.endswith(".toml"):
            with open(config_path, "rb") as f:
                config_data = tomllib.load(f)
        else:
            raise ValueError(f"Unsupported configuration file extension: {config_path}")

        # Process environment variables in api_key fields
        for conn_name, conn_config in config_data.get("connections", {}).items():
            for key, value in conn_config.items():
                if isinstance(value, str) and value.startswith("env:"):
                    env_var = value.split(":", 1)[1]
                    conn_config[key] = os.environ.get(env_var, "")

        return Config(**config_data)
