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
    Resolves a configuration value into a callable or an object instance.

    Supports multiple input formats commonly used in configuration files:

    - ``None`` or ``""``: Returns ``None``.
    - ``dict`` with a class key: Instantiates the class with remaining dict entries as kwargs.
      Example: ``{"class": "my_module.MyClass", "param": 42}`` → ``MyClass(param=42)``
    - ``str``: Imports the dotted path. Classes are instantiated; functions are returned as-is.
      Example: ``"my_module.my_func"`` → ``my_func``
      Example: ``"my_module.MyClass"`` → ``MyClass()``
    - ``class``: Instantiated with no arguments.
    - ``callable``: Returned as-is (lambdas, function objects, callable instances).
    - Other types: Accepted only if their type is listed in ``allow_types``.

    Args:
        item: The configuration value to resolve.
        class_key: Key used to identify the class in dict configs (default: ``"class"``).
        debug_name: Human-readable label for error messages
            (e.g., ``"logger"``, ``"api_key_check"``).
        allow_types: Additional types to accept as valid values without transformation.

    Returns:
        A callable, an object instance, or ``None``.

    Raises:
        ValueError: If the input cannot be resolved to a valid callable or instance.
    """
    if item is None or item == "":
        return None
    if isinstance(item, dict):
        if class_key in item:
            args = dict(item)
            class_name = args.pop(class_key)
            constructor = resolve_callable(class_name)
            return constructor(**args)
        elif dict not in (allow_types or []):
            raise ValueError(
                f"'{class_key}' key is missing in {debug_name or 'item'} config: {item}"
            )
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
