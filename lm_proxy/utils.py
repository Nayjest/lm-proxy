"""Common usage utility functions."""

import os
import json
import inspect
import logging
from typing import Any, Callable, Union
from datetime import datetime, date, time

from microcore.utils import resolve_callable
from starlette.requests import Request


def resolve_obj_path(obj, path: str, default=None):
    """
    Resolves dotted path supporting
    attributes, dict keys and list indices.
    """
    for part in path.split("."):
        try:
            if isinstance(obj, dict):
                obj = obj[part]
            elif isinstance(obj, list):
                part = int(part)  # Convert to int for list indexing
                obj = obj[part]
            else:
                obj = getattr(obj, part)
        except (AttributeError, KeyError, TypeError, ValueError, IndexError):
            return default
    return obj


def resolve_instance_or_callable(
    item: Union[str, Callable, dict, object],
    class_key: str = "class",
    debug_name: str = None,
    allow_types: list[type] = None,
) -> Callable | object | None:
    """
    Resolves a class instance or callable from various configuration formats.
    """
    if item is None or item == "":
        return None
    if isinstance(item, dict):
        if class_key not in item:
            raise ValueError(
                f"'{class_key}' key is missing in {debug_name or 'item'} config: {item}"
            )
        args = dict(item)
        class_name = args.pop(class_key)
        constructor = resolve_callable(class_name)
        return constructor(**args)
    if isinstance(item, str):
        fn = resolve_callable(item)
        return fn() if inspect.isclass(fn) else fn
    if callable(item):
        return item() if inspect.isclass(item) else item
    if allow_types and any(isinstance(item, t) for t in allow_types):
        return item
    raise ValueError(f"Invalid {debug_name or 'item'} config: {item}")


class CustomJsonEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles datetime / date / time, pydantic models, etc.
    """

    def default(self, o):
        if isinstance(o, (datetime, date, time)):
            return o.isoformat()
        if hasattr(o, "model_dump"):
            return o.model_dump()
        if hasattr(o, "dict"):
            return o.dict()
        if hasattr(o, "__dict__"):
            return o.__dict__
        return super().default(o)


def get_client_ip(request: Request) -> str:
    """
    Extract the client's IP address from the request.
    """
    # Try different headers in order of preference
    if forwarded_for := request.headers.get("X-Forwarded-For"):
        return forwarded_for.split(",")[0].strip()
    if real_ip := request.headers.get("X-Real-IP"):
        return real_ip
    if forwarded := request.headers.get("Forwarded"):
        # Parse Forwarded header (RFC 7239)
        if "for=" in forwarded:
            return forwarded.split("for=")[1].split(";")[0].strip()

    # Fallback to direct client
    return request.client.host if request.client else "unknown"


def replace_env_strings_recursive(data: Any) -> Any:
    """
    Recursively traverses dicts and lists, replacing all string values
    that start with 'env:' with the corresponding environment variable.
    For example, a string "env:VAR_NAME" will be replaced by the value of the
    environment variable "VAR_NAME".
    """
    if isinstance(data, dict):
        return {k: replace_env_strings_recursive(v) for k, v in data.items()}
    if isinstance(data, list):
        return [replace_env_strings_recursive(i) for i in data]
    if isinstance(data, str) and data.startswith("env:"):
        env_var_name = data[4:]
        if env_var_name not in os.environ:
            logging.warning("Environment variable '%s' not found", env_var_name)
        return os.environ.get(env_var_name, "")
    return data


# Headers that should not be overridden by user-provided extra_headers
# These are either set by the transport layer or contain sensitive information
SENSITIVE_HEADERS = frozenset(
    {
        # Authentication headers - always use configured credentials
        "authorization",
        "www-authenticate",
        # Content metadata - set by transport layer
        "content-length",
        "content-type",
        "transfer-encoding",
        # Connection control headers
        "connection",
        "keep-alive",
        "upgrade",
        # Caching headers
        "cache-control",
        "etag",
        "if-none-match",
        # Proxy headers
        "proxy-authorization",
        "proxy-connection",
        # Security headers
        "strict-transport-security",
        # Host header - identifies the target server
        "host",
        # Range headers for partial content
        "range",
        "if-range",
        # HTTP/2 and HTTP/3 specific
        ":method",
        ":path",
        ":scheme",
        ":authority",
        "te",
        "trailer",
    }
)


def filter_sensitive_headers(headers: dict[str, str]) -> dict[str, str]:
    """
    Filter out sensitive headers that should not be overridden by user-provided headers.

    Args:
        headers: Dictionary of headers to filter

    Returns:
        Dictionary with sensitive headers removed
    """
    return {k: v for k, v in headers.items() if k.lower() not in SENSITIVE_HEADERS}


def merge_headers(
    base_headers: dict[str, str] | None,
    override_headers: dict[str, str] | None,
    filter_sensitive: bool = True,
) -> dict[str, str]:
    """
    Merge two header dictionaries, with override_headers taking precedence.

    Args:
        base_headers: Base headers (e.g., from config)
        override_headers: Override headers (e.g., from request)
        filter_sensitive: Whether to filter sensitive headers from the result

    Returns:
        Merged headers dictionary
    """
    result = dict(base_headers) if base_headers else {}
    if override_headers:
        result.update(override_headers)
    if filter_sensitive:
        result = filter_sensitive_headers(result)
    return result
