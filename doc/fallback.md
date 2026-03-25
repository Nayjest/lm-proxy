# Fallback Strategy

> *When your primary LLM stumbles, don't crash — cascade gracefully.*

## Overview

The **Fallback** strategy tries each configured connection in sequence,
returning the first successful response.

If a connection fails, the error is logged and the next one is attempted.
If all connections fail, the last exception is re-raised.

**Available since:** v3.1.0  
**Class:** `lm_proxy.strategies.Fallback`

## Quick Start

```toml
[routing]
"*" = "fallback.*"

[groups.default]
api_keys = ["KEY1"]

[connections.openai]
api_base = "https://api.openai.com/v1/"
api_key = "env:OPENAI_API_KEY"

[connections.local]
api_base = "http://127.0.0.1:1235/v1/"
api_key = "not required"
init_params = { max_retries = 0 }

[connections.fallback]
class = "lm_proxy.strategies.Fallback"
connections = ["local.openai/gpt-oss-20b", "openai.gpt-5.2"]
```

```bash
lm-proxy --config config.toml
```

## Configuration Formats

### Dict format (with parameter overrides)

Use a dictionary when you need to override parameters per connection in the fallback chain:

```toml
[connections.fallback]
class = "lm_proxy.strategies.Fallback"

[connections.fallback.connections.local]
model = "openai/gpt-oss-20b"

[connections.fallback.connections.openai]
model = "gpt-5.2"
reasoning_effort = "low"
```

Or in inline form:

```toml
[connections.fallback]
class = "lm_proxy.strategies.Fallback"
connections = { local = { model = "openai/gpt-oss-20b" }, openai = { model = "gpt-5.2", reasoning_effort = "low" } }
```

Keys must match connection names defined in `[connections]`.
Dict values are merged into the kwargs passed to the underlying LLM function.

### List format (shorthand)

When no parameter overrides are needed:

```toml
[connections.fallback]
class = "lm_proxy.strategies.Fallback"
connections = ["local", "openai"]
```

To specify a model override in list format, use dot notation:

```toml
connections = ["local.openai/gpt-oss-20b", "openai.gpt-5.2"]
```

This is equivalent to `{ local = { model = "openai/gpt-oss-20b" }, openai = { model = "gpt-5.2" } }`.

## Requirements

- **Minimum 2 connections.** A single-connection fallback wouldn't be much of a fallback.
- All referenced connection names must exist in `[connections]` at runtime.

## Behavior

1. Connections are tried **in insertion order**.
2. On success, the response is returned immediately — remaining connections are never called.
3. On failure, a warning is logged with the exception details, then the next connection is attempted.
4. If the **last** connection fails, the exception propagates to the caller.

### Log output example

```
12:34:56 INFO: Fallback strategy: using "local" connection
12:34:57 WARNING: Connection 'local' failed (APIError: rate limit exceeded), trying next one...
12:34:57 INFO: Fallback strategy: using "openai" connection
```

## Combining with Other Strategies

Fallback composes naturally with other connection types.
For instance, use a load balancer as the primary and a dedicated server as the safety net:

```toml
[connections.cluster]
class = "my_module.LoadBalancer"
connections = ["server1", "server2"]

[connections.dedicated_backup]
api_base = "https://backup.example.com/v1/"
api_key = "env:BACKUP_API_KEY"

[connections.safe_route]
class = "lm_proxy.strategies.Fallback"
connections = { cluster = {}, dedicated_backup = {} }
```