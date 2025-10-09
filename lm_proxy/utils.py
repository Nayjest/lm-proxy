import json
import inspect
from typing import Union, Callable
from datetime import datetime, date, time

from microcore.utils import resolve_callable
from starlette.requests import Request


def resolve_obj_path(obj, path: str, default=None):
    """Resolves dotted path supporting both attributes and dict keys."""
    for part in path.split("."):
        try:
            if isinstance(obj, dict):
                obj = obj[part]
            else:
                obj = getattr(obj, part)
        except (AttributeError, KeyError, TypeError):
            return default
    return obj


def resolve_instance_or_callable(
    item: Union[str, Callable, dict], class_key: str = "class", debug_name: str = None
) -> Callable:
    if not item:
        return None
    if isinstance(item, dict):
        if class_key not in item:
            raise ValueError(
                f"'{class_key}' key is missing in {debug_name or 'item'} config: {item}"
            )
        class_name = item.pop(class_key)
        constructor = resolve_callable(class_name)
        return constructor(**item)
    if isinstance(item, str):
        fn = resolve_callable(item)
        return fn() if inspect.isclass(fn) else fn
    if callable(item):
        return item() if inspect.isclass(item) else item
    else:
        raise ValueError(f"Invalid {debug_name or 'item'} config: {item}")


class CustomJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, time):
            return obj.isoformat()
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        elif hasattr(obj, "model_dump"):
            return obj.model_dump()
        elif hasattr(obj, "dict"):
            return obj.dict()
        return super().default(obj)


def get_client_ip(request: Request) -> str:
    # Try different headers in order of preference
    if forwarded_for := request.headers.get("X-Forwarded-For"):
        return forwarded_for.split(",")[0].strip()
    if real_ip := request.headers.get("X-Real-IP"):
        return real_ip
    if forwarded := request.headers.get("Forwarded"):
        # Parse Forwarded header (RFC 7239)
        return forwarded.split("for=")[1].split(";")[0].strip()

    # Fallback to direct client
    return request.client.host if request.client else "unknown"
