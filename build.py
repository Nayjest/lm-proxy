import re
from pathlib import Path
import subprocess

NAMES = [
    "lm-proxy",
    "llm-proxy-server",
    "ai-proxy-server",
    "lm-proxy-server",
    "openai-http-proxy",
    "inference-proxy",
    "oai-proxy"
]


def replace_name(name, path="pyproject.toml"):
    Path(path).write_text(
        re.sub(
            r'^name\s*=\s*".*?"',
            f'name = "{name}"',
            Path(path).read_text(encoding="utf-8"),
            count=1, flags=re.M
        )
    )


for n in NAMES:
    print(f"=== Building for project name: {n}")
    replace_name(n)
    subprocess.run(["poetry", "build"], check=True)
replace_name(NAMES[0])
print("All builds completed.")
