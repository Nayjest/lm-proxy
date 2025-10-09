import asyncio
import logging
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime

import microcore as mc
from ..bootstrap import env

if TYPE_CHECKING:
    from lm_proxy.core import ChatCompletionRequest, Group


@dataclass
class LogEntry:
    request: "ChatCompletionRequest" = field()
    response: Optional[mc.LLMResponse] = field(default=None)
    error: Optional[Exception] = field(default=None)
    group: "Group" = field(default=None)
    connection: str = field(default=None)
    api_key_id: Optional[str] = field(default=None)
    remote_addr: Optional[str] = field(default=None)
    created_at: Optional[str] = field(default=None)
    duration: Optional[float] = field(default=None)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        data = self.__dict__.copy()
        if self.request:
            data["request"] = self.request.model_dump(mode="json")
        return data


async def log(log_entry: LogEntry):
    if log_entry.duration is None and log_entry.created_at:
        log_entry.duration = (datetime.now() - log_entry.created_at).total_seconds()
    for handler in env.config.loggers:
        # check if it is async, then run both sync and async loggers in non-blocking way (sync too)
        if asyncio.iscoroutinefunction(handler):
            asyncio.create_task(handler(log_entry))
        else:
            try:
                handler(log_entry)
            except Exception as e:
                logging.error("Error in logger handler: %s", e)
                raise e


async def log_non_blocking(
    log_entry: LogEntry,
) -> Optional[asyncio.Task]:
    if env.config.loggers:
        task = asyncio.create_task(log(log_entry))
        return task
