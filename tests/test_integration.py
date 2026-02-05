import microcore as mc
import requests
from openai import OpenAI

from tests.conftest import ServerFixture


def configure_mc_to_use_local_proxy(cfg: ServerFixture):
    mc.configure(
        LLM_API_TYPE="openai",
        LLM_API_BASE=f"http://127.0.0.1:{cfg.port}/v1",
        LLM_API_KEY=cfg.api_key,
        MODEL=cfg.model,
    )


def test_france_capital_query(server_config_fn: ServerFixture):
    configure_mc_to_use_local_proxy(server_config_fn)
    response = mc.llm("What is the capital of France?\n (!) Respond with 1 word.")
    assert "paris" in response.lower()


def test_direct_api_call(server_config_fn: ServerFixture):
    """Test directly calling the API without microcore."""
    cfg = server_config_fn
    response = requests.post(
        f"http://127.0.0.1:{cfg.port}/v1/chat/completions",
        json={
            "model": cfg.model,
            "messages": [{"role": "user", "content": "What is the capital of France?"}],
        },
        headers={"Authorization": f"Bearer {cfg.api_key}"},
        timeout=120,
    )

    assert response.status_code == 200
    data = response.json()
    assert "Paris" in data["choices"][0]["message"]["content"]


def test_streaming_response(server_config_fn: ServerFixture):
    configure_mc_to_use_local_proxy(server_config_fn)
    chunks = []
    mc.llm(
        "Count from 1 to 5, each number as english word (one, two, ...) on a new line",
        callback=lambda chunk: chunks.append(str(chunk).lower()),
    )
    full_response = "".join(chunks)
    for word in ["one", "two", "three", "four", "five"]:
        assert word in full_response


def test_models(server_config_fn: ServerFixture):
    """Test the models endpoint."""
    cfg = server_config_fn
    client = OpenAI(api_key=cfg.api_key, base_url=f"http://127.0.0.1:{cfg.port}/v1")
    models = {m.id for m in client.models.list().data}
    assert models == {"my-gpt", "*"}
