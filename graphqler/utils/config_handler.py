from graphqler import config
from graphqler.utils.file_utils import get_project_root, get_graphqler_root
import tomllib
import os


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


def generate_new_config(config_file_to_write: str) -> None:
    """Generates the new config file by copying from static/config.toml

    Args:
        config_file_to_write (str): The config file to write
    """
    # copy from the base path of the graphqler package
    project_root = get_graphqler_root()
    os.system(f"cp {project_root}/examples/config.toml {config_file_to_write}")


def does_config_file_exist_in_path(path: str) -> bool:
    """Checks if the config file exists in the path

    Args:
        path (str): The path to check

    Returns:
        bool: Whether the config file exists
    """
    return os.path.exists(f"{path}/{config.CONFIG_FILE_NAME}")
