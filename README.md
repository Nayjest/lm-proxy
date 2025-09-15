<p align="center">
  <img src="https://img.shields.io/github/license/Nayjest/lm-proxy?color=blue" alt="License">
  <a href="https://pypi.org/project/lm-proxy/"><img src="https://img.shields.io/pypi/v/lm-proxy?color=blue" alt="PyPI"></a>
  <a href="https://github.com/Nayjest/lm-proxy/actions/workflows/tests.yml"><img src="https://github.com/Nayjest/lm-proxy/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/Nayjest/lm-proxy/actions/workflows/code-style.yml"><img src="https://github.com/Nayjest/lm-proxy/actions/workflows/code-style.yml/badge.svg" alt="Code Style"></a>
</p>

# LM-Proxy

**LM-Proxy** is an OpenAI-compatible HTTP proxy server for various Large Language Models (LLMs) inference. 
It provides a unified interface for working with different AI providers through a single API endpoint that follows the OpenAI format.
Stream like OpenAI, authenticate with your own API keys, and keep clients unchanged.
## ✨ Features

- **Provider Agnostic**: Connect to OpenAI, Anthropic, Google AI, local models, and more using a single API
- **Unified Interface**: Access all models through the standard OpenAI API format
- **Dynamic Routing**: Route requests to different LLM providers based on model name patterns
- **Stream Support**: Full streaming support for real-time responses
- **API Key Management**: Configurable API key validation and access control
- **Easy Configuration**: Simple TOML configuration files for setup

## 🚀 Getting Started

### Installation

```bash
pip install lm-proxy
```

### Quick Start

1. Create a `config.toml` file:

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

2. Start the server:

```bash
lm-proxy
```

3. Use it with any OpenAI-compatible client:

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
```

### Environment Variables

You can use environment variables in your configuration file by prefixing values with `env:`:

```toml
[connections.openai]
api_key = "env:OPENAI_API_KEY"
```

Load these from a `.env` file or set them in your environment before starting the server.

## 🔌 API Usage

LM-Proxy implements the OpenAI chat completions API endpoint. You can use any OpenAI-compatible client to interact with it.

### Endpoint

```
POST /v1/chat/completions
```

### Request Format

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

### Response Format

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

## 🛠️ Advanced Usage

### Custom API Key Validation

You can implement your own API key validation function:

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
