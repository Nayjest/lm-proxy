def load_yaml_config(config_path: str) -> dict:
    try:
        import yaml
    except ImportError as e:
        raise ImportError(
            "Missing optional dependency 'PyYAML'. "
            "For using YAML configuration files with LM-Proxy, "
            "please install it with following command: 'pip install pyyaml'."
        ) from e

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
