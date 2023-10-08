"""Linker: Creates a networkx graph and stores it in a pickle file for use later on during fuzzing
The linker does the following:
- Serialize all the objects (Objects, Queries, Mutations, InputObjects, Enums)
- Generate a graph of object dependencies
- Attach queries to the object node
- Attach mutations related to the object node
"""

from pathlib import Path
from .serializers import ObjectsSerializer
from utils.file_utils import read_yaml_to_dict

import constants


class Linker:
    def __init__(self, save_path: str):
        self.save_path = save_path
        self.compiled_queries_save_path = Path(save_path) / constants.COMPILED_QUERIES_FILE_NAME
        self.compiled_objects_save_path = Path(save_path) / constants.COMPILED_OBJECTS_FILE_NAME
        self.compiled_mutationss_save_path = Path(save_path) / constants.COMPILED_MUTATIONS_FILE_NAME

        self.compiled_queries = read_yaml_to_dict(self.compiled_queries_save_path)
        self.compiled_objects = read_yaml_to_dict(self.compiled_objects_save_path)
        self.compiled_mutations = read_yaml_to_dict(self.compiled_mutationss_save_path)

    def run(self):
        """Generater the NX graph and saave it as a pickle"""
        pass
