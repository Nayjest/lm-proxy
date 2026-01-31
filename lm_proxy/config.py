"""
Configuration models for LM-Proxy settings.
This module defines Pydantic models that match the structure of config.toml.
"""

import os
from enum import StrEnum
from typing import Union, Callable, Dict, Optional
from importlib.metadata import entry_points

from pydantic import BaseModel, Field, ConfigDict

from .utils import resolve_instance_or_callable, replace_env_strings_recursive
from .loggers import TLogger


class ModelListingMode(StrEnum):
    """
    Enum for model listing modes in the /models endpoint.
    """

    # Show all models from API provider matching the patterns (not implemented yet)
    EXPAND_WILDCARDS = "expand_wildcards"
    # Ignore wildcard models, show only exact model names
    # (keys of the config.routing dict not containing * or ?)
    IGNORE_WILDCARDS = "ignore_wildcards"
    # Show everything as is, including wildcard patterns
    AS_IS = "as_is"


class Group(BaseModel):
    """User group configuration."""
    api_keys: list[str] = Field(default_factory=list)
    allowed_connections: str = Field(default="*")  # Comma-separated list or "*"

    def allows_connecting_to(self, connection_name: str) -> bool:
        """Check if the group allows access to the specified connection."""
        if self.allowed_connections == "*":
            return True
        allowed = [c.strip() for c in self.allowed_connections.split(",") if c.strip()]
        return connection_name in allowed


TApiKeyCheckResult = Optional[Union[str, tuple[str, dict]]]
TApiKeyCheckFunc = Callable[[str | None], TApiKeyCheckResult]


class Config(BaseModel):
    """Main configuration model matching config.toml structure."""

    model_config = ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
    )
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    ssl_keyfile: str | None = None
    """ Path to SSL key file for HTTPS support, if None, HTTP is used. """
    ssl_certfile: str | None = None
    """ Path to SSL certificate file for HTTPS support, if None, HTTP is used. """
    api_prefix: str = "/v1"
    """ Prefix for API endpoints, default is /v1 """
    dev_autoreload: bool = False
    connections: dict[str, Union[dict, Callable, str]] = Field(
        ...,  # Required field (no default)
        description="Dictionary of connection configurations",
        examples=[{"openai": {"api_key": "sk-..."}}],
    )
    routing: dict[str, str] = Field(default_factory=dict)
    """ model_name_pattern* => connection_name.< model | * >, example: {"gpt-*": "oai.*"} """
    groups: dict[str, Group] = Field(default_factory=lambda: {"default": Group()})
    api_key_check: Union[str, TApiKeyCheckFunc, dict] = Field(
        default="lm_proxy.api_key_check.check_api_key_in_config",
        description="Function to check Virtual API keys",
    )
    loggers: list[Union[str, dict, TLogger]] = Field(default_factory=list)
    encryption_key: str = Field(
        default="Eclipse",
        description="Key for encrypting sensitive data (must be explicitly set)",
    )
    model_listing_mode: ModelListingMode = Field(
        default=ModelListingMode.AS_IS,
        description="How to handle wildcard models in /models endpoint",
    )
    model_info: dict[str, dict] = Field(
        default_factory=dict,
        description="Additional metadata for /models endpoint",
    )
    components: dict[str, Union[str, Callable, dict]] = Field(default_factory=dict)
    middleware: list[Union[str, Callable, dict]] = Field(default_factory=list)

    def __init__(self, **data):
        super().__init__(**data)
        self.api_key_check = resolve_instance_or_callable(
            self.api_key_check,
            debug_name="check_api_key",
        )

    @staticmethod
    def _load_raw(config_path: str | os.PathLike = "config.toml") -> Union["Config", Dict]:
        config_ext = os.path.splitext(config_path)[1].lower().lstrip(".")
        for entry_point in entry_points(group="config.loaders"):
            if config_ext == entry_point.name:
                loader = entry_point.load()
                config_data = loader(config_path)
                return config_data

        raise ValueError(f"No loader found for configuration file extension: {config_ext}")

    @staticmethod
    def load(config_path: str | os.PathLike = "config.toml") -> "Config":
        """
        Load configuration from a TOML or Python file.

        Args:
            config_path: Path to the config.toml file

        Returns:
            Config object with parsed configuration
        """
        config = Config._load_raw(config_path)
        if isinstance(config, dict):
            config = replace_env_strings_recursive(config)
            config = Config(**config)
        elif not isinstance(config, Config):
            raise TypeError("Loaded configuration must be a dict or Config instance")
        return config
