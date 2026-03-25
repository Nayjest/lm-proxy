"""Fallback strategy: tries connections in order until one succeeds."""

import logging

import microcore as mc
from microcore import ui

from pydantic import BaseModel, field_validator

from ..bootstrap import env


class Fallback(BaseModel):
    """
    Tries each connection in sequence, returning the first successful response.

    If a connection fails, the error is logged and the next one is attempted.
    If all connections fail, the last exception is re-raised.
    """

    connections: dict[str, dict] | list[str]

    @field_validator("connections")
    @classmethod
    def validate_connections(cls, v: list[str] | dict[str]) -> dict[str]:
        if len(v) < 2:
            raise ValueError("Fallback requires at least 2 connections")
        if isinstance(v, list):
            v_dict = {}
            for conn_name_and_model in v:
                if "." in conn_name_and_model:
                    conn_name, model = conn_name_and_model.split(".", 1)
                    v_dict[conn_name] = {"model": model}
                else:
                    v_dict[conn_name_and_model] = {}
            return v_dict
        return v

    async def __call__(self, *args, **kwargs):
        for conn_name, override_params in self.connections.items():
            logging.info(
                f"Fallback strategy: using \"{ui.green(conn_name)}\" connection"
                + ((", overriden params: " + ui.yellow(override_params)) if override_params else "")
            )
            if conn_name not in env.connections:
                raise ValueError(
                    f"Fallback connection '{conn_name}' not found. "
                    f"Available: {list(env.connections.keys())}"
                )
            kw_args = dict(kwargs)
            kw_args.update(override_params or {})
            fn: mc.types.LLMAsyncFunctionType = env.connections[conn_name]
            try:
                return await fn(*args, **kw_args)
            except Exception as e:
                is_last = conn_name == list(self.connections)[-1]
                if is_last:
                    logging.error("All fallback connections failed, last error: %s", e)
                    raise
                logging.warning(
                    "Connection '%s' failed (%s: %s), trying next one...",
                    conn_name, type(e).__name__, e,
                )
