"""Class for fuzzer

Fuzzer actually does 2 things:
0. Serializes the YAML files into built-in types for easier use when fuzzing
1. Creates the object-dependency graph for fuzzing
2. Run the actual fuzzing
"""

from pathlib import Path
from graph import GraphGenerator
from utils.file_utils import read_yaml_to_dict

import constants


class Fuzzer:
    def __init__(self, save_path: str, url: str):
        """Initializes the fuzzer, reading information from the compiled files

        Args:
            save_path (str): Save directory path
            url (str): URL for graphql introspection query to hit
        """
        self.save_path = save_path
        self.url = url

        self.compiled_queries_save_path = Path(save_path) / constants.COMPILED_QUERIES_FILE_NAME
        self.compiled_objects_save_path = Path(save_path) / constants.COMPILED_OBJECTS_FILE_NAME
        self.compiled_mutations_save_path = Path(save_path) / constants.COMPILED_MUTATIONS_FILE_NAME
        self.extracted_enums_save_path = Path(save_path) / constants.ENUM_LIST_FILE_NAME
        self.extracted_input_objects_save_path = Path(save_path) / constants.INPUT_OBJECT_LIST_FILE_NAME

        self.queries = read_yaml_to_dict(self.compiled_queries_save_path)
        self.objects = read_yaml_to_dict(self.compiled_objects_save_path)
        self.mutations = read_yaml_to_dict(self.compiled_mutations_save_path)
        self.input_objects = read_yaml_to_dict(self.extracted_input_objects_save_path)
        self.enums = read_yaml_to_dict(self.extracted_enums_save_path)

        self.dependency_graph = GraphGenerator(save_path).get_dependency_graph()

    def run(self):
        pass
