"""
HTTP headers forwarder LM-Proxy.
"""
from dataclasses import dataclass, field

from lm_proxy.base_types import RequestContext

SENSITIVE_HEADERS = {
    # Authentication headers - always use configured credentials
    "authorization",
    "www-authenticate",
    # Content metadata - set by transport layer
    "content-length",
    "content-type",
    "transfer-encoding",
    # Connection control headers
    "connection",
    "keep-alive",
    "upgrade",
    # Caching headers
    "cache-control",
    "etag",
    "if-none-match",
    # Proxy headers
    "proxy-authorization",
    "proxy-connection",
    # Security headers
    "strict-transport-security",
    # Host header - identifies the target server
    "host",
    # Range headers for partial content
    "range",
    "if-range",
    # HTTP/2 and HTTP/3 specific
    ":method",
    ":path",
    ":scheme",
    ":authority",
    "te",
    "trailer",
}


@dataclass
class HTTPHeadersForwarder:
    ignore_headers: set[str] = field(default_factory=lambda: frozenset(SENSITIVE_HEADERS))
    white_list_headers: set[str] = field(default_factory=set)

    async def __call__(self, ctx: RequestContext) -> None:
        """
        Forward HTTP headers from the incoming request to the LLM provider,
        excluding headers in the ignore list.
        If white_list_headers is set, only those headers will be forwarded.
        """
        if not ctx.http_request or not ctx.http_request.headers:
            return
        headers_to_forward = {}
        for name, value in ctx.http_request.headers.items():
            name_lower = name.lower()
            if name_lower in self.ignore_headers:
                continue
            if self.white_list_headers and name_lower not in self.white_list_headers:
                continue
            headers_to_forward[name] = value

        if not headers_to_forward:
            return
        if "extra_headers" not in ctx.llm_params:
            ctx.llm_params["extra_headers"] = {}
        ctx.llm_params["extra_headers"].update(headers_to_forward)
