"""
Rate limiting handler for LM-Proxy.

Provides sliding window rate limiting per API key / IP address / connection / user group / global.
"""
import threading
import time
from dataclasses import dataclass, field
from enum import Enum

from lm_proxy.base_types import RequestContext
from lm_proxy.errors import OpenAIHTTPException


class RateLimitScope(str, Enum):
    API_KEY = "api_key"
    CONNECTION = "connection"
    GROUP = "group"
    IP = "ip"
    GLOBAL = "global"


@dataclass
class RateLimiter:
    """
    Sliding window rate limiter. Thread-safe.
    Raises HTTP 429 when limit exceeded.

    Args:
        max_requests: Maximum requests allowed per window.
        window_seconds: Window size in seconds.
        max_buckets: Trigger cleanup when bucket count exceeds this.
        per: Scope for rate limiting
            ("api_key", "connection", "group", "ip", "global").
    """
    max_requests: int = 60
    window_seconds: float = 60.0
    per: RateLimitScope = RateLimitScope.API_KEY
    max_buckets: int = 10000
    _buckets: dict[str, list[float]] = field(default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _get_key(self, ctx: RequestContext) -> str:
        match self.per:
            case RateLimitScope.API_KEY:
                return ctx.api_key_id or "anon"
            case RateLimitScope.CONNECTION:
                return ctx.connection or "default"
            case RateLimitScope.GROUP:
                return ctx.group or "default"
            case RateLimitScope.IP:
                return ctx.remote_addr or "anon"
            case RateLimitScope.GLOBAL:
                return "global"

    async def __call__(self, ctx: RequestContext) -> None:
        """
        Check rate limit for request.

        Raises:
            HTTPException: 429 if rate limit exceeded.
        """
        key = self._get_key(ctx)
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            if len(self._buckets) > self.max_buckets:
                self._buckets = {
                    k: v for k, v in self._buckets.items()
                    if v and v[-1] > cutoff
                }

            timestamps = [t for t in self._buckets.get(key, []) if t > cutoff]

            if len(timestamps) >= self.max_requests:
                retry_after = int(timestamps[0] - cutoff) + 1
                raise OpenAIHTTPException(
                    message=f"Rate limit exceeded: {self.max_requests}/{int(self.window_seconds)}s",
                    status_code=429,
                    error_type="rate_limit_error",
                    code="rate_limit_exceeded",
                    headers={"Retry-After": str(retry_after)},
                )

            self._buckets[key] = [*timestamps, now]
