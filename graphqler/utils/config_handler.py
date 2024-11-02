from graphqler import config
import tomllib


def parse_config(config_file: str) -> dict:
    """
    Parse the config, and return the dictionary
    """
    config = {}
    with open(config_file, "rb") as f:
        config = tomllib.load(f)

    if len(config.keys()) == 0:
        print(f"(!) No items in config file: {config_file}")
        exit(1)

    return config


def set_config(new_config: dict):
    """Sets config to the new file using reflection on the constants module

    Args:
        new_config (dict): The configuration dictionary
    """
    for k, v in new_config.items():
        if hasattr(config, k):
            setattr(config, k, v)
        else:
            print(f"(!) Unknown configuration {k}, skipping it")
