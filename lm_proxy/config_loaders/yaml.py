"""YAML configuration loader."""


def load_yaml_config(config_path: str) -> dict:
    """Loads a YAML configuration file and returns its contents as a dictionary."""
    try:
        import yaml  # pylint: disable=import-outside-toplevel
    except ImportError as e:
        raise ImportError(
            "Missing optional dependency 'PyYAML'. "
            "For using YAML configuration files with LM-Proxy, "
            "please install it with the following command: 'pip install pyyaml'."
        ) from e

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
