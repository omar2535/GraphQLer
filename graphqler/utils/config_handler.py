from graphqler import constants
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


def set_constants_with_config(config: dict):
    """Sets constants to the config file using reflection on the constants module

    Args:
        config (dict): The configuration dictionary
    """
    for k, v in config.items():
        if hasattr(constants, k):
            setattr(constants, k, v)
        else:
            print(f"(!) Unknown configuration {k}, skipping it")
