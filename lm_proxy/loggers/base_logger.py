import abc
from dataclasses import dataclass, field

from lm_proxy.utils import resolve_instance_or_callable

from ..utils import resolve_obj_path
from .core import LogEntry


class AbstractLogEntryTransformer(abc.ABC):
    @abc.abstractmethod
    def __call__(self, log_entry: LogEntry) -> dict:
        raise NotImplementedError()


class LogEntryTransformer(AbstractLogEntryTransformer):
    def __init__(self, **kwargs):
        self.mapping = kwargs

    def __call__(self, log_entry: LogEntry) -> dict:
        result = {}
        for key, path in self.mapping.items():
            result[key] = resolve_obj_path(log_entry, path)
        return result


class AbstractLogWriter(abc.ABC):
    @abc.abstractmethod
    def __call__(self, logged_data: dict) -> dict:
        raise NotImplementedError()


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

    def _transform(self, log_entry: LogEntry) -> dict:
        return (
            self.entry_transformer(log_entry)
            if self.entry_transformer
            else log_entry.to_dict()
        )

    def __call__(self, log_entry: LogEntry):
        self.log_writer(self._transform(log_entry))
