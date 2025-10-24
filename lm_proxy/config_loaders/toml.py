import tomllib


def load_toml_config(config_path: str) -> dict:
    with open(config_path, "rb") as f:
        return tomllib.load(f)
