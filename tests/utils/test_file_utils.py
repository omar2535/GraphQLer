import os
import json
import yaml
from pathlib import Path
from utils.file_utils import initialize_file, write_json_to_file, write_dict_to_yaml, read_yaml_to_dict


def test_initialize_file():
    file_path = Path("test.txt")
    initialize_file(file_path)
    assert file_path.exists()
    os.remove(file_path)


def test_write_json_to_file():
    contents = {"name": "John", "age": 30, "city": "New York"}
    output_file = "test.json"
    write_json_to_file(contents, output_file)
    with open(output_file) as f:
        data = json.load(f)
    assert data == contents
    os.remove(output_file)


def test_write_dict_to_yaml():
    contents = {"name": "John", "age": 30, "city": "New York"}
    output_file = "test.yaml"
    write_dict_to_yaml(contents, output_file)
    with open(output_file) as f:
        data = yaml.safe_load(f)
    assert data == contents
    os.remove(output_file)


def test_read_yaml_to_dict():
    read_path = Path("test.yaml")
    contents = {"name": "John", "age": 30, "city": "New York"}
    with open(read_path, "w") as f:
        yaml.dump(contents, f)
    data = read_yaml_to_dict(read_path)
    assert data == contents
    os.remove(read_path)
