<h1 align="center"><a href="#">LM-Proxy</a></h1>
<p align="center">
  <b>Lightweight, OpenAI-compatible HTTP proxy server</b><br>unifying access to multiple <b>Large Language Model providers</b> and local inference <br>through a single, standardized API endpoint.  
</p>
<p align="center">
  <a href="https://pypi.org/project/lm-proxy/"><img src="https://img.shields.io/pypi/v/lm-proxy?color=blue" alt="PyPI"></a>
  <a href="https://github.com/Nayjest/lm-proxy/actions/workflows/tests.yml"><img src="https://github.com/Nayjest/lm-proxy/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/Nayjest/lm-proxy/actions/workflows/code-style.yml"><img src="https://github.com/Nayjest/lm-proxy/actions/workflows/code-style.yml/badge.svg" alt="Code Style"></a>
  <img src="https://raw.githubusercontent.com/Nayjest/lm-proxy/main/coverage.svg" alt="Code Coverage">
  <a href="https://github.com/Nayjest/lm-proxy/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Nayjest/lm-proxy?color=d08aff" alt="License"></a>
</p>

Built with Python, FastAPI and [MicroCore](https://github.com/Nayjest/ai-microcore), **LM-Proxy** seamlessly integrates cloud providers like Google, Anthropic, and OpenAI, as well as local PyTorch-based inference, while maintaining full compatibility with OpenAI's API format.  

It works as a drop-in replacement for OpenAI's API, allowing you to switch between cloud providers and local models without modifying your existing client code.  

**LM-Proxy** supports **real-time token streaming**, **secure Virtual API key management**, and can be used both as an importable Python library and as a standalone HTTP service. Whether you're building production applications or experimenting with different models, LM-Proxy eliminates integration complexity and keeps your codebase **provider-agnostic**.


## Table of Contents
- [Overview](#lm-proxy)
- [Features](#-features)
- [Getting Started](#-getting-started)
  - [Installation](#installation)
  - [Quick Start](#quick-start)
- [Configuration](#-configuration)
  - [Basic Structure](#basic-structure)
  - [Environment Variables](#environment-variables)
- [Proxy API Keys vs. Provider API Keys](#-proxy-api-keys-vs-provider-api-keys)
- [API Usage](#-api-usage)
  - [Chat Completions Endpoint](#chat-completions-endpoint)
  - [Models List Endpoint](#models-list-endpoint)
- [User Groups Configuration](#-user-groups-configuration)
  - [Basic Group Definition](#basic-group-definition)
  - [Group-based Access Control](#group-based-access-control)
  - [Connection Restrictions](#connection-restrictions)
  - [Custom API Key Validation](#custom-api-key-validation)
- [Advanced Usage](#%EF%B8%8F-advanced-usage)
  - [Dynamic Model Routing](#dynamic-model-routing)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

- **Provider Agnostic**: Connect to OpenAI, Anthropic, Google AI, local models, and more using a single API
- **Unified Interface**: Access all models through the standard OpenAI API format
- **Dynamic Routing**: Route requests to different LLM providers based on model name patterns
- **Stream Support**: Full streaming support for real-time responses
- **API Key Management**: Configurable API key validation and access control
- **Easy Configuration**: Simple TOML configuration files for setup

## 🚀 Getting Started

### Requirements
Python 3.11 | 3.12 | 3.13

### Installation

```bash
pip install lm-proxy
```

### Quick Start

#### 1. Create a `config.toml` file:

```toml
host = "0.0.0.0"
port = 8000

[connections]
[connections.openai]
api_type = "open_ai"
api_base = "https://api.openai.com/v1/"
api_key = "env:OPENAI_API_KEY"

[connections.anthropic]
api_type = "anthropic"
api_key = "env:ANTHROPIC_API_KEY"

[routing]
"gpt*" = "openai.*"
"claude*" = "anthropic.*"
"*" = "openai.gpt-3.5-turbo"

[groups.default]
api_keys = ["YOUR_API_KEY_HERE"]
```
> **Note**
> To enhance security, consider storing upstream API keys in operating system environment variables rather than embedding them directly in the configuration file. You can reference these variables in the configuration using the env:<VAR_NAME> syntax.

#### 2. Start the server:

```bash
lm-proxy
```
Alternatively, run it as a Python module:
```bash
python -m lm_proxy
```

#### 3. Use it with any OpenAI-compatible client:

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY_HERE",
    base_url="http://localhost:8000/v1"
)

completion = client.chat.completions.create(
    model="gpt-5",  # This will be routed to OpenAI based on config
    messages=[{"role": "user", "content": "Hello, world!"}]
)
print(completion.choices[0].message.content)
```

Or use the same endpoint with Claude models:

```python
completion = client.chat.completions.create(
    model="claude-opus-4-1-20250805",  # This will be routed to Anthropic based on config
    messages=[{"role": "user", "content": "Hello, world!"}]
)
```

## 📝 Configuration

LM-Proxy is configured through a TOML file that specifies connections, routing rules, and access control.

### Basic Structure

```toml
host = "0.0.0.0"  # Interface to bind to
port = 8000       # Port to listen on
dev_autoreload = false  # Enable for development

# API key validation function (optional)
check_api_key = "lm_proxy.core.check_api_key"

# LLM Provider Connections
[connections]

[connections.openai]
api_type = "open_ai"
api_base = "https://api.openai.com/v1/"
api_key = "env:OPENAI_API_KEY"

[connections.google]
api_type = "google_ai_studio"
api_key = "env:GOOGLE_API_KEY"

[connections.anthropic]
api_type = "anthropic"
api_key  = "env:ANTHROPIC_API_KEY"

# Routing rules (model_pattern = "connection.model")
[routing]
"gpt*" = "openai.*"     # Route all GPT models to OpenAI
"claude*" = "anthropic.*"  # Route all Claude models to Anthropic
"gemini*" = "google.*"  # Route all Gemini models to Google
"*" = "openai.gpt-3.5-turbo"  # Default fallback

# Access control groups
[groups.default]
api_keys = [
    "KEY1",
    "KEY2"
]

# optional
[[loggers]]
class = 'lm_proxy.loggers.BaseLogger'
[loggers.log_writer]
class = 'lm_proxy.loggers.log_writers.JsonLogWriter'
file_name = 'storage/json.log'
[loggers.entry_transformer]
class = 'lm_proxy.loggers.LogEntryTransformer'
completion_tokens = "response.usage.completion_tokens"
prompt_tokens = "response.usage.prompt_tokens"
prompt = "request.messages"
response = "response"
group = "group"
connection = "connection"
api_key_id = "api_key_id"
remote_addr = "remote_addr"
created_at = "created_at"
duration = "duration"
```

### Environment Variables

You can reference environment variables in your configuration file by prefixing values with `env:`.  

For example:

```toml
[connections.openai]
api_key = "env:OPENAI_API_KEY"
```

At runtime, LM-Proxy automatically retrieves the value of the target variable
(OPENAI_API_KEY) from your operating system’s environment or from a .env file, if present.

###  .env Files

By default, LM-Proxy looks for a `.env` file in the current working directory
and loads environment variables from it.

You can refer to the [.env.template](https://github.com/Nayjest/lm-proxy/blob/main/.env.template)
 file for an example:
```dotenv
OPENAI_API_KEY=sk-u........
GOOGLE_API_KEY=AI........
ANTHROPIC_API_KEY=sk-ant-api03--vE........

# "1", "TRUE", "YES", "ON", "ENABLED", "Y", "+" are true, case-insensitive.
# See https://github.com/Nayjest/ai-microcore/blob/v4.4.3/microcore/configuration.py#L36
LM_PROXY_DEBUG=no
```

You can also control `.env` file usage with the `--env` command-line option:

```bash
# Use a custom .env file path
lm-proxy --env="path/to/your/.env"
# Disable .env loading
lm-proxy --env=""
```

## 🔑 Proxy API Keys vs. Provider API Keys

LM-Proxy utilizes two distinct types of API keys to facilitate secure and efficient request handling.

- **Proxy API Key (Virtual API Key, Client API Key):**  
A unique key generated and managed within the LM-Proxy.  
Clients use these keys to authenticate their requests to the proxy's API endpoints.  
Each Client API Key is associated with a specific group, which defines the scope of access and permissions for the client's requests.  
These keys allow users to securely interact with the proxy without direct access to external service credentials.



- **Provider API Key (Upstream API Key):**
A key provided by external LLM inference providers (e.g., OpenAI, Anthropic, Mistral, etc.) and configured within the LM-Proxy.  
The proxy uses these keys to authenticate and forward validated client requests to the respective external services.  
Provider API Keys remain hidden from end users, ensuring secure and transparent communication with provider APIs.

This distinction ensures a clear separation of concerns: 
Virtual API Keys manage user authentication and access within the proxy, 
while Upstream API Keys handle secure communication with external providers.

## 🔌 API Usage

LM-Proxy implements the OpenAI chat completions API endpoint. You can use any OpenAI-compatible client to interact with it.

### Chat Completions Endpoint

```http
POST /v1/chat/completions
```

#### Request Format

```json
{
  "model": "gpt-3.5-turbo",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"}
  ],
  "temperature": 0.7,
  "stream": false
}
```

#### Response Format

```json
{
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The capital of France is Paris."
      },
      "finish_reason": "stop"
    }
  ]
}
```


### Models List Endpoint


List and describe all models available through the API.


```http
GET /v1/models
```

The **LM-Proxy** dynamically builds the models list based on routing rules defined in `config.routing`.  
Routing keys can reference both **exact model names** and **model name patterns** (e.g., `"gpt*"`, `"claude*"`, etc.).

By default, wildcard patterns are displayed as-is in the models list (e.g., `"gpt*"`, `"claude*"`).  
This behavior can be customized via the `model_listing_mode` configuration option:

```
model_listing_mode = "as_is" | "ignore_wildcards" | "expand_wildcards"
```

Available modes:

- **`as_is`** *(default)* — Lists all entries exactly as defined in the routing configuration, including wildcard patterns.  
- **`ignore_wildcards`** — Excludes wildcard patterns, showing only explicitly defined model names.  
- **`expand_wildcards`** — Expands wildcard patterns by querying each connected backend for available models *(feature not yet implemented)*.

To obtain a complete and accurate model list in the current implementation,
all supported models must be explicitly defined in the routing configuration, for example:
```toml
[routing]
"gpt-4" = "my_openai_connection.*"
"gpt-5" = "my_openai_connection.*"
"gpt-8"= "my_openai_connection.gpt-3.5-turbo"
"claude-4.5-sonnet" = "my_anthropic_connection.claude-sonnet-4-5-20250929"
"claude-4.1-opus" = "my_anthropic_connection.claude-opus-4-1-20250805"
[connections]
[connections.my_openai_connection]
api_type = "open_ai"
api_base = "https://api.openai.com/v1/"
api_key  = "env:OPENAI_API_KEY"
[connections.my_anthropic_connection]
api_type = "anthropic"
api_key  = "env:ANTHROPIC_API_KEY"
```



#### Response Format

```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-6",
      "object": "model",
      "created": 1686935002,
      "owned_by": "organization-owner"
    },
    {
      "id": "claude-5-sonnet",
      "object": "model",
      "created": 1686935002,
      "owned_by": "organization-owner"
    }
  ]
}
```

## 🔒 User Groups Configuration

The `[groups]` section in the configuration defines access control rules for different user groups.  
Each group can have its own set of virtual API keys and permitted connections.

### Basic Group Definition

```toml
[groups.default]
api_keys = ["KEY1", "KEY2"]
allowed_connections = "*"  # Allow access to all connections
```

### Group-based Access Control

You can create multiple groups to segment your users and control their access:

```toml
# Admin group with full access
[groups.admin]
api_keys = ["ADMIN_KEY_1", "ADMIN_KEY_2"]
allowed_connections = "*"  # Access to all connections

# Regular users with limited access
[groups.users]
api_keys = ["USER_KEY_1", "USER_KEY_2"]
allowed_connections = "openai,anthropic"  # Only allowed to use specific connections

# Free tier with minimal access
[groups.free]
api_keys = ["FREE_KEY_1", "FREE_KEY_2"]
allowed_connections = "openai"  # Only allowed to use OpenAI connection
```

### Connection Restrictions

The `allowed_connections` parameter controls which upstream providers a group can access:

- `"*"` - Group can use all configured connections
- `"openai,anthropic"` - Comma-separated list of specific connections the group can use

This allows fine-grained control over which users can access which AI providers, enabling features like:

- Restricting expensive models to premium users
- Creating specialized access tiers for different user groups
- Implementing usage quotas per group
- Billing and cost allocation by user group

### Custom API Key Validation

For more advanced authentication needs,
you can implement a custom validator function:

```python
# my_validators.py
def validate_api_key(api_key: str) -> str | None:
    """
    Validate an API key and return the group name if valid.
    
    Args:
        api_key: The API key to validate
        
    Returns:
        The name of the group if valid, None otherwise
    """
    if api_key == "secret-key":
        return "admin"
    elif api_key.startswith("user-"):
        return "users"
    return None
```

Then reference it in your config:

```toml
check_api_key = "my_validators.validate_api_key"
```
> **NOTE**
> In this case, the `api_keys` lists in groups are ignored, and the custom function is responsible for all validation logic.


## 🛠️ Advanced Usage
### Dynamic Model Routing

The routing section allows flexible pattern matching with wildcards:

```toml
[routing]
"gpt-4*" = "openai.gpt-4"           # Route gpt-4 requests to OpenAI GPT-4
"gpt-3.5*" = "openai.gpt-3.5-turbo" # Route gpt-3.5 requests to OpenAI
"claude*" = "anthropic.*"           # Pass model name as-is to Anthropic
"gemini*" = "google.*"              # Pass model name as-is to Google
"custom*" = "local.llama-7b"        # Map any "custom*" to a specific local model
"*" = "openai.gpt-3.5-turbo"        # Default fallback for unmatched models
```
### Advanced Configuration Examples

- [Simple load-balancer configuration](https://github.com/Nayjest/lm-proxy/blob/main/examples/load_balancer_config.py)  
  This example demonstrates how to set up a load balancer that randomly
distributes requests across multiple language model servers using the lm_proxy.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
© 2025 Vitalii Stepanenko
