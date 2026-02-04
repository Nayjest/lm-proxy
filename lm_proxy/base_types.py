"""Base types used in LM-Proxy."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Awaitable, Callable, List, Optional, TYPE_CHECKING, Union

import microcore as mc
from pydantic import BaseModel
from starlette.requests import Request


if TYPE_CHECKING:
    from .config import Group


class ChatCompletionRequest(BaseModel):
    """
    Request model for chat/completions endpoint.
    """
    model: str
    messages: List[mc.Msg | dict]
    # | dict --> support of messages with lists of dicts
    # defining distinct content-parts inside 'content' field
    stream: Optional[bool] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stop: Optional[List[str]] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    user: Optional[str] = None


@dataclass
class RequestContext:  # pylint: disable=too-many-instance-attributes
    """
    Stores information about a single LLM request/response cycle for usage in middleware.
    """
    id: Optional[str] = field(default_factory=lambda: str(uuid.uuid4()))
    request: Optional[ChatCompletionRequest] = field(default=None)
    http_request: Optional[Request] = field(default=None)
    response: Optional[mc.LLMResponse] = field(default=None)
    error: Optional[Exception] = field(default=None)
    group: Optional["Group"] = field(default=None)
    connection: Optional[str] = field(default=None)
    model: Optional[str] = field(default=None)
    llm_params: dict = field(default_factory=dict)  # kwargs for microcore.llm() call
    api_key_id: Optional[str] = field(default=None)
    remote_addr: Optional[str] = field(default=None)
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    duration: Optional[float] = field(default=None)
    user_info: Optional[dict] = field(default=None)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Export as dictionary."""
        data = self.__dict__.copy()
        del data["http_request"]
        if self.request:
            data["request"] = self.request.model_dump(mode="json")
        return data


THandler = Callable[
    [RequestContext],
    Union[Awaitable[None], None]
]