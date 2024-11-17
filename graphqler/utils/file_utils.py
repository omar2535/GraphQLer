from pathlib import Path
import yaml
import json
import shutil


def initialize_file(file_path: str | Path):
    """Initialize file_path with an empty file creating any folders along the way

    Args:
        file_path (str | Path): The path to the file
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    open(file_path, "w").close()


def intialize_file_if_not_exists(file_path: Path):
    """Initialize file_path with an empty file creating any folders along the way if it does not exist

    Args:
        file_path (Path): The path to the file
    """
    if not file_path.exists():
        initialize_file(file_path)


def recreate_path(dir_path: Path):
    """Recreate a directory

    Args:
        dir_path (Path): The directory path
    """
    # Convert the path to a Path object
    path = Path(dir_path)

    # Remove the directory if it exists
    shutil.rmtree(path, ignore_errors=True)

    # Re-create the directory
    path.mkdir(parents=True, exist_ok=True)


def get_or_create_file(file_path: Path) -> Path:
    """Gets a file if it exists, otherwise creates it

    Args:
        file_path (Path): File path

    Returns:
        Path: The file path
    """
    if not file_path.exists():
        initialize_file(file_path)
    return file_path


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
