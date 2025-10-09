import microcore as mc
import requests
from tests.conftest import ServerFixture


def configure_mc(cfg: ServerFixture):
    mc.configure(
        LLM_API_TYPE="openai",
        LLM_API_BASE=f"http://127.0.0.1:{cfg.port}/v1",  # Test server port
        LLM_API_KEY=cfg.api_key,  # Not used but required
        MODEL=cfg.model,  # Will be routed according to test_config.toml
    )


def test_france_capital_query(server_config_fn: ServerFixture):
    configure_mc(server_config_fn)
    response = mc.llm("What is the capital of France?\n (!) Respond with 1 word.")
    assert (
        "paris" == response.lower().strip()
    ), f"Expected 'Paris' in response, got: {response}"


def test_direct_api_call(server_config_fn: ServerFixture):
    """Test directly calling the API without microcore."""
    cfg = server_config_fn
    response = requests.post(
        f"http://127.0.0.1:{cfg.port}/v1/chat/completions",
        json={
            "model": cfg.model,
            "messages": [{"role": "user", "content": "What is the capital of France?"}],
        },
        headers={
            "Content-Type": "application/json",
            "authorization": f"bearer {cfg.api_key}",
        },
    )

    assert (
        response.status_code == 200
    ), f"Expected status code 200, got {response.status_code}"

    data = response.json()
    assert "choices" in data, f"Missing 'choices' in response: {data}"
    assert len(data["choices"]) > 0, "No choices returned"
    assert (
        "message" in data["choices"][0]
    ), f"Missing 'message' in first choice: {data['choices'][0]}"
    assert (
        "Paris" in data["choices"][0]["message"]["content"]
    ), f"Expected 'Paris' in response, got: {data['choices'][0]['message']['content']}"


def test_streaming_response(server_config_fn: ServerFixture):
    configure_mc(server_config_fn)
    collected_text = []
    mc.llm(
        "Count from 1 to 5, each number as english word (one, two, ...) on a new line",
        callback=lambda chunk: collected_text.append(str(chunk).lower()),
    )
    full_response = "".join(collected_text)
    for i in ["one", "two", "three", "four", "five"]:
        assert i in full_response, f"Expected '{i}' in response, got: {full_response}"
    assert len(collected_text) >= 1
