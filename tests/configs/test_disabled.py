import os
import logging
from types import SimpleNamespace

import pytest
from starlette.requests import Request

from lm_proxy.utils import (
    resolve_instance_or_callable,
    replace_env_strings_recursive,
    resolve_obj_path,
    get_client_ip,
)


def test_resolve_instance_or_callable():
    assert resolve_instance_or_callable(None) is None

    obj1, obj2 = object(), object()
    ins = resolve_instance_or_callable(obj1, allow_types=[object])
    assert ins is obj1 and ins is not obj2

    with pytest.raises(ValueError):
        resolve_instance_or_callable(123)

    with pytest.raises(ValueError):
        resolve_instance_or_callable([])

    with pytest.raises(ValueError):
        resolve_instance_or_callable({})

    assert resolve_instance_or_callable(lambda: 42)() == 42

    class MyClass:
        def __init__(self, value=0):
            self.value = value

    res = resolve_instance_or_callable(lambda: MyClass(10), allow_types=[MyClass])
    assert not isinstance(res, MyClass) and res().value == 10

    ins = resolve_instance_or_callable(MyClass(20), allow_types=[MyClass])
    assert isinstance(ins, MyClass) and ins.value == 20
    assert (
        resolve_instance_or_callable("lm_proxy.utils.resolve_instance_or_callable")
        is resolve_instance_or_callable
    )

    ins = resolve_instance_or_callable(
        {"class": "lm_proxy.loggers.JsonLogWriter", "file_name": "test.log"}
    )
    assert ins.__class__.__name__ == "JsonLogWriter" and ins.file_name == "test.log"


def test_replace_env_strings_recursive(caplog):
    os.environ["TEST_VAR1"] = "env_value1"
    os.environ["TEST_VAR2"] = "env_value2"
    assert replace_env_strings_recursive("env:TEST_VAR1") == "env_value1"

    caplog.set_level(logging.WARNING)
    assert replace_env_strings_recursive("env:NON_EXIST") == ""
    assert len(caplog.records) == 1

    assert replace_env_strings_recursive([["env:TEST_VAR1"]]) == [["env_value1"]]
    assert replace_env_strings_recursive({"data": {"field": "env:TEST_VAR1"}}) == {
        "data": {"field": "env_value1"}
    }


def test_resolve_obj_path():
    o = SimpleNamespace(a=SimpleNamespace(b=dict(c=[None, lambda x: x * 2])))
    assert resolve_obj_path(o, "a.b.c.1")(10) == 20
    assert resolve_obj_path(o, "a.b.cc.1", "no") == "no"


def test_get_client_ip():
    request = Request(
        scope={
            "type": "http",
            "headers": [],
        }
    )
    assert get_client_ip(request) == "unknown"

    request = Request(
        scope={
            "type": "http",
            "headers": [(b"x-forwarded-for", b"192.168.1.1")],
        }
    )
    assert get_client_ip(request) == "192.168.1.1"

    request = Request(
        scope={
            "type": "http",
            "headers": [(b"x-forwarded-for", b"192.168.1.1, 10.0.0.2")],
        }
    )
    assert get_client_ip(request) == "192.168.1.1"  # should take the first IP

    request = Request(
        scope={
            "type": "http",
            "headers": [(b"x-real-ip", b"203.0.113.5")],
        }
    )
    assert get_client_ip(request) == "203.0.113.5"

    request = Request(
        scope={
            "type": "http",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }
    )
    assert get_client_ip(request) == "127.0.0.1"

    request = Request(
        scope={
            "type": "http",
            "headers": [
                (b"x-real-ip", b"203.0.113.5"),
                (b"x-forwarded-for", b"192.168.1.1, 10.0.0.2"),
            ],
        }
    )
    assert get_client_ip(request) == "192.168.1.1"  # x-forwarded-for has priority

    # RFC 7239 Forwarded header
    result = get_client_ip(
        Request(
            scope={
                "type": "http",
                "headers": [(b"forwarded", b"for=192.0.2.60;proto=http;by=203.0.113.43")],
            }
        )
    )
    assert result == "192.0.2.60"

    # IPv6 address
    assert (
        get_client_ip(
            Request(
                scope={
                    "type": "http",
                    "headers": [
                        (b"user-agent", b"Mozilla/5.0"),
                        (b"x-forwarded-for", b"2001:0db8:85a3:0000:0000:8a2e:0370:7334"),
                        (b"content-type", b"application/json"),
                    ],
                }
            )
        )
        == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    )

    """Test when client IP is in scope"""
    assert (
        get_client_ip(
            Request(
                scope={
                    "type": "http",
                    "headers": [],
                    "client": ("192.168.1.100", 8080),
                }
            )
        )
        == "192.168.1.100"
    )
