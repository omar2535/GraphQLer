from pathlib import Path
import yaml
import json


def initialize_file(file_path: Path):
    """Initialize file_path with an empty file creating any folders along the way

    Args:
        file_path (Path): The path to the file
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    open(file_path, "w").close()


def write_json_to_file(contents: dict, output_file: str | Path):
    """Write JSON to a file

    Args:
        contents (dict): Contents of the JSON
        output_file (str): Output file path
    """
    with open(output_file, "w") as file_handle:
        json.dump(contents, file_handle, indent=4)


def write_dict_to_yaml(contents: dict, output_file: str | Path):
    """Writes dict to YAML file

    Args:
        contents (dict): Contents of the YAML
        output_file (str): Output file path
    """
    yaml_data = yaml.dump(contents, default_flow_style=False)
    with open(output_file, "w") as yaml_file:
        yaml_file.write(yaml_data)


def read_yaml_to_dict(read_path: Path) -> dict:
    """Reads yaml file to dict

    Args:
        read_path (Path): Path of the yaml file

    Returns:
        dict: Dictionary of the YAML file contents
    """
    return yaml.safe_load(read_path.read_text())
