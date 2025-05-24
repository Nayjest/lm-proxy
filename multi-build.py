import re
from pathlib import Path
import subprocess

NAMES = (
    ("lm-proxy", "LM-Proxy"),
    ("llm-proxy-server", "LLM Proxy Server"),
    ("ai-proxy-server", "AI Proxy Server"),
    ("lm-proxy-server", "LM Proxy Server"),
    ("openai-http-proxy", "OpenAI HTTP Proxy"),
    ("inference-proxy", "Inference Proxy"),
    ("oai-proxy", "OAI Proxy"),
)
FILES = (
    "pyproject.toml",
    "README.md",
)


def replace_name(old_names: tuple, new_names: tuple, files: list[str] = None):
    files = files or FILES
    for i in range(len(old_names)):
        old_name = old_names[i]
        new_name = new_names[i]
        for path in files:
            p = Path(path)
            p.write_text(
                re.sub(
                    fr'(?<![\\/]){old_name}\b',
                    new_name,
                    p.read_text(encoding="utf-8"),
                    flags=re.M
                ), encoding="utf-8"
            )

prev = NAMES[0]
for n in NAMES[1:]+(NAMES[0]):
    print(f"Building for project name: {n[0]}...")
    replace_name(prev, n)
    subprocess.run(["poetry", "build"], check=True)
print("All builds completed.")
