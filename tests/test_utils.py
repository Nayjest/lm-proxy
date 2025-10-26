import os
import logging

import pytest
from lm_proxy.utils import resolve_instance_or_callable, replace_env_strings_recursive


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
    assert resolve_instance_or_callable(
        "lm_proxy.utils.resolve_instance_or_callable"
    ) is resolve_instance_or_callable

    ins = resolve_instance_or_callable({
        'class': 'lm_proxy.loggers.JsonLogWriter',
        'file_name': 'test.log'
    })
    assert ins.__class__.__name__ == 'JsonLogWriter' and ins.file_name == 'test.log'


def test_replace_env_strings_recursive(caplog):
    os.environ['TEST_VAR1'] = 'env_value1'
    os.environ['TEST_VAR2'] = 'env_value2'
    assert replace_env_strings_recursive("env:TEST_VAR1") == 'env_value1'

    caplog.set_level(logging.WARNING)
    assert replace_env_strings_recursive("env:NON_EXIST") == ''
    assert len(caplog.records) == 1

    assert replace_env_strings_recursive([["env:TEST_VAR1"]]) == [['env_value1']]
    assert replace_env_strings_recursive(
        {"data": {"field": "env:TEST_VAR1"}}
    ) == {"data": {"field": "env_value1"}}
