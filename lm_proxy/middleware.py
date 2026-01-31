from typing import Callable, Awaitable, Union
from dataclasses import dataclass, field

from .base_types import RequestContext


@dataclass
class BaseMiddleware:
    """Base class for middleware components."""

    async def __call__(self, ctx: RequestContext, next_handler: Callable) -> None:
        """Process the request context and call the next handler in the chain."""
        await next_handler()


TMiddleware = Union[BaseMiddleware, Callable[[RequestContext, Callable], Awaitable[None]]]


async def run_middleware_chain(
    middlewares: list[TMiddleware],
    ctx: RequestContext,
    handler: Callable[[], Awaitable[None]],
) -> None:
    if not middlewares:
        await handler()
        return

    def wrap(mw, next_fn):
        async def wrapped():
            await mw(ctx, next_fn)  # ctx captured from closure

        return wrapped

    chain = handler
    for mw in reversed(middlewares):
        chain = wrap(mw, chain)

    await chain()