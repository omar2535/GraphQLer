from graphqler import config
from graphqler.utils.file_utils import get_graphqler_root
import tomllib
import os


def write_config_to_toml(path: str) -> None:
    """Write current live-config values to a TOML file.

    Reads ``examples/config.toml`` to discover the canonical set of
    user-configurable keys — no static list required.  For each key in the
    template, the current value is read from the live ``config`` module so
    any in-process changes are captured.  Keys absent from the live module
    fall back to the template's default value.
    """
    template_path = get_graphqler_root() / "examples" / "config.toml"
    with open(template_path, "rb") as fh:
        template: dict = tomllib.load(fh)

    lines = ["# GraphQLer configuration\n"]
    for key, template_value in template.items():
        if key == "CUSTOM_HEADERS":
            continue  # written as a TOML section below
        value = getattr(config, key, template_value)
        if isinstance(value, bool):
            lines.append(f"{key} = {'true' if value else 'false'}\n")
        elif isinstance(value, (int, float)):
            lines.append(f"{key} = {value}\n")
        elif isinstance(value, list):
            lines.append(f"{key} = {value}\n")
        elif value is None:
            lines.append(f'{key} = ""\n')
        else:
            escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"\n')

    lines.append("\n[CUSTOM_HEADERS]\n")
    headers: dict = getattr(config, "CUSTOM_HEADERS", None) or template.get("CUSTOM_HEADERS", {})
    for k, v in headers.items():
        ev = str(v).replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{k} = "{ev}"\n')

    with open(path, "w") as fh:
        fh.writelines(lines)


def parse_config(config_obj: str | dict) -> dict:
    """
    Parse the config, and return the dictionary.
    If it's a dictionary, just parses the config object directly
    Otherwise parses it out of a TOML file
    """
    config = {}
    if isinstance(config_obj, dict):
        config = config_obj
    elif isinstance(config_obj, str):
        with open(config_obj, "rb") as f:
            config = tomllib.load(f)

    if len(config.keys()) == 0:
        print(f"(!) No items in config {config_obj}")
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
