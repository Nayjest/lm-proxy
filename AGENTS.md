# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## What this is

LM-Proxy is a lightweight, OpenAI-compatible HTTP proxy/gateway (FastAPI + [MicroCore](https://github.com/Nayjest/ai-microcore)) that unifies access to multiple LLM providers (OpenAI, Anthropic, Google, local PyTorch inference) behind a single OpenAI-format API. It runs as a standalone server or as an importable Python library.

## Commands

```bash
make install          # pip install -e .
make run              # fastapi run lm_proxy  (or: python -m lm_proxy / lm-proxy)
make test             # pytest --log-cli-level=INFO
make integration-test # pytest tests/test_integration.py -v
make cs               # flake8 .   (lint)
make black            # black .     (format; line-length 100)
make build            # python multi-build.py  (build dist packages)
```

Run a single test: `pytest tests/test_core.py::test_name -v`

`pytest` config lives in `pyproject.toml`: `asyncio_mode = "auto"` (async tests need no decorator), `testpaths = ["tests"]`.

Optional provider deps are extras: `pip install -e .[anthropic,google]` or `.[all]`; `.[test]` for the test toolchain.

The server loads `config.toml` from the cwd by default (`lm-proxy --config <path>` to override; `--env` to pick a `.env` file). The repo-root `config.toml` is the dev/reference config; more samples live in `examples/`.

## Architecture

Request flow for `POST /v1/chat/completions` (`lm_proxy/core.py:chat_completions`):
1. `fail_if_service_disabled()` → `check()` validates the **virtual/client API key** via `config.api_key_check`, returning a group name (and optional `user_info`).
2. `resolve_connection_and_model()` matches the requested model against `config.routing` patterns (fnmatch wildcards). Rule values are `"connection.model"` or `"connection.*"` (`*` passes the requested model name through unchanged).
3. Group `allowed_connections` is enforced (comma-separated connection names or `"*"`; groups also hold the `api_keys` list checked by the default validator).
4. `before` handlers (middleware) run sequentially, each receiving a `RequestContext`.
5. The resolved connection — a MicroCore `llm_async_function` — is invoked. Streaming requests go through `process_stream()` (SSE `text/event-stream`); non-streaming return a JSON `choices` array.
6. `log_non_blocking()` fires all configured loggers as async tasks.

`GET /v1/models` (`models_endpoint.py`) lists `config.routing` keys filtered by the caller group's allowed connections; `model_listing_mode` controls wildcard-pattern handling and `model_info` merges extra metadata per model.

Key modules:
- `app.py` — Typer CLI (`cli_app`) + FastAPI factory (`web_app`). Endpoints registered under `config.api_prefix` (default `/v1`).
- `bootstrap.py` — `bootstrap()` loads `.env`, sets up logging/debug, then `Env.init()` builds the **`env` runtime singleton**: resolves connections (into MicroCore async LLM functions), components, loggers, and `before` handlers. Most runtime code reads global `env.config`, `env.connections`, etc.
- `config.py` — Pydantic `Config` model (`extra="forbid"`). `Config.load()` dispatches by file extension to a loader registered as a `config.loaders` entry point (see `pyproject.toml`), supporting **TOML / YAML / JSON / Python** configs. Env-var refs (`env:VAR_NAME`) are expanded via `replace_env_strings_recursive`.
- `base_types.py` — `ChatCompletionRequest` (the OpenAI-shaped request) and `RequestContext` (the per-request object threaded through handlers and loggers).
- `utils.py:resolve_instance_or_callable` — the central extensibility primitive: turns a config value (dotted string `"my.module.fn"`, dict with `class`/`function` key + kwargs, or callable) into a live object. Used for connections, api_key_check, handlers, loggers, components.

Extension points (all configured by reference, no core changes needed):
- **Connections** (`[connections]`) — a MicroCore config dict (`api_type`, keys) OR a custom async callable. See `strategies/fallback.py` for an example custom connection.
- **api_key_check** — `api_key_check/` has `check_api_key_in_config` (default), `CheckAPIKeyWithRequest` (external HTTP/OIDC validation), and `allow_all`. A validator returns a group name (or `(group, user_info)` tuple), or falsy to reject.
- **Handlers / middleware** (`[[before]]`) — `handlers/` ships `RateLimiter` and `HTTPHeadersForwarder`. Any callable taking a `RequestContext`.
- **Loggers** (`[[loggers]]`) — `loggers.py` (`BaseLogger`, `JsonLogWriter`, `LogEntryTransformer`). Run non-blocking.

## Conventions

- Errors surfaced to clients use OpenAI's error envelope (`{"error": {"message","type","param","code"}}`); see `errors.py:OpenAIHTTPException`.
- Debug mode (`LM_PROXY_DEBUG` env or `--debug`) raises full tracebacks and sets DEBUG logging; otherwise exceptions are logged and a sanitized error returned. CLI flags override env.
- Streaming errors are not HTTP errors: they arrive as a final SSE chunk carrying an `error` object and `finish_reason: "error"`, followed by `data: [DONE]`.
- `config.encryption_key` salts the MD5 `api_key_id` hash used to identify keys in logs — client API keys are never logged raw.
- Supported Python: 3.11–3.13.
