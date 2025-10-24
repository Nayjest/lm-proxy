import abc
import json
import os
from dataclasses import dataclass, field
from typing import Union, Callable

from .base_types import RequestContext
from .utils import CustomJsonEncoder, resolve_instance_or_callable, resolve_obj_path


class AbstractLogEntryTransformer(abc.ABC):
    @abc.abstractmethod
    def __call__(self, request_context: RequestContext) -> dict:
        raise NotImplementedError()


class AbstractLogWriter(abc.ABC):
    @abc.abstractmethod
    def __call__(self, logged_data: dict) -> dict:
        raise NotImplementedError()


class LogEntryTransformer(AbstractLogEntryTransformer):
    def __init__(self, **kwargs):
        self.mapping = kwargs

    def __call__(self, request_context: RequestContext) -> dict:
        result = {}
        for key, path in self.mapping.items():
            result[key] = resolve_obj_path(request_context, path)
        return result


@dataclass
class BaseLogger:
    log_writer: AbstractLogWriter | str | dict
    entry_transformer: AbstractLogEntryTransformer | str | dict = field(default=None)

    def __post_init__(self):
        self.entry_transformer = resolve_instance_or_callable(
            self.entry_transformer,
            debug_name="logging.<logger>.entry_transformer",
        )
        self.log_writer = resolve_instance_or_callable(
            self.log_writer,
            debug_name="logging.<logger>.log_writer",
        )

    def _transform(self, request_context: RequestContext) -> dict:
        return (
            self.entry_transformer(request_context)
            if self.entry_transformer
            else request_context.to_dict()
        )

    def __call__(self, request_context: RequestContext):
        self.log_writer(self._transform(request_context))


@dataclass
class JsonLogWriter(AbstractLogWriter):
    file_name: str

    def __post_init__(self):
        dir_path = os.path.dirname(self.file_name)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        # Create the file if it doesn't exist
        with open(self.file_name, "a", encoding="utf-8"):
            pass

    def __call__(self, logged_data: dict):
        with open(self.file_name, "a", encoding="utf-8") as f:
            f.write(json.dumps(logged_data, cls=CustomJsonEncoder) + "\n")


TLogger = Union[BaseLogger, Callable[[RequestContext], None]]
