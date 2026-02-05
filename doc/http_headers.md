# HTTP Header Management

**LM-Proxy** provides flexible HTTP header manipulation for requests routed to upstream LLM providers
— fully compatible with major inference APIs (OpenAI, Google, Anthropic).

Supported operations:
- **Static header injection** — add fixed headers (e.g., organization IDs, routing tags) to every request for a specific connection.
- **Dynamic header forwarding** — pass headers from incoming client requests (e.g., trace IDs, correlation tokens) through to the backend.

---

## Static Headers

Define headers per connection in the configuration file. These are injected into every upstream request for that connection.

**Typical use cases:**
- Internal routing keys or service identifiers
- Static authentication tokens for custom gateways
- Billing or cost-allocation tags recognized by the provider

**Configuration:**
```yaml
connections:
  custom_gpt:
    api_type: "openai"
    model: "gpt-5"
    api_key: "sk-..."
    http_headers:
      X-Service-ID: "lm-proxy-gateway"
      X-Department: "engineering"
```

## Dynamic Header Forwarding

For scenarios where headers must pass from the client through the proxy to the provider, use the `HTTPHeadersForwarder` lifecycle handler.

**Typical use cases:**
- Distributed tracing (OpenTelemetry, Jaeger, etc.)
- Forwarding tenant or user context in multi-tenant setups

### Behavior

The forwarder automatically strips sensitive protocol headers
(`Host`, `Content-Length`, `Authorization`) to prevent protocol corruption or credential leaks.
For tighter control, specify an explicit allow-list.

**Forward all non-sensitive headers:**
```yaml
before:
  - class: "lm_proxy.handlers.HTTPHeadersForwarder"
```

**Allow-list mode (recommended for production):**
```yaml
before:
  - class: "lm_proxy.handlers.HTTPHeadersForwarder"
    white_list_headers:
      - "x-request-id"
      - "x-correlation-id"
      - "traceparent"
```

---

## Full Example

A complete `config.yaml` combining static injection and dynamic forwarding:
```yaml
port: 8000

connections:
  upstream_ai:
    api_type: "openai"
    api_base: "https://api.internal.corp/v1"
    api_key: "sk-internal"
    http_headers:
      X-Source: "proxy-node-1"

before:
  - class: "lm_proxy.handlers.HTTPHeadersForwarder"
    white_list_headers:
      - "x-trace-id"

routing:
  "*": "upstream_ai.*"

groups:
  default:
    api_keys: [...]
```

With this configuration, every request to `upstream_ai` includes the static `X-Source` header, and any client-supplied `x-trace-id` is forwarded transparently.

---

## See Also

- [AI MicroCore Documentation — Custom HTTP Headers](https://github.com/Nayjest/ai-microcore/blob/main/doc/features/http_headers.md)
- [HTTPHeadersForwarder Source Code](https://github.com/Nayjest/lm-proxy/blob/main/lm_proxy/handlers/forward_http_headers.py)