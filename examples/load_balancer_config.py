"""
# Load Balancer Configuration Example

This example demonstrates how to set up a load balancer that randomly
distributes requests across multiple language model servers using the lm_proxy.

Steps to run:
1. Save this script as `load_balancer_config.py`.
2. Create a `.env` file in the same directory with your API keys.
3. Run the lm-proxy server with this configuration:
```bash
lm-proxy --config load_balancer_config.py
```
"""
import logging
import os
import random
from dotenv import load_dotenv
from lm_proxy.config import Config, Group
from lm_proxy.bootstrap import env

load_dotenv('.env')

async def load_balancer(*args, **kwargs):
    connection_name = random.choice(
        [i for i in env.config.connections.keys() if i != "load_balancer"]
    )
    logging.info(f"Load balancer selected connection: {connection_name}")
    kwargs.pop("model", None)  # remove model to avoid confusion
    return await env.connections[connection_name](*args, **kwargs)

config = Config(
    connections=dict(
        load_balancer=load_balancer,
        server1={
            "api_type": "openai",
            "api_base": "https://api.openai.com/v1",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": "gpt-5-mini",
        },
        server2={
            "api_type": "anthropic",
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "model": "claude-3-5-haiku-20241022",
        }
    ),
    routing={"*": "load_balancer.*"},
    groups=dict(default=Group(connections="load_balancer", api_keys=["KEY1"])),
)