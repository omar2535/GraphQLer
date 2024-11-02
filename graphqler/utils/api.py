"""Class for the target API
- Used to retrieve information about the API
"""

from pathlib import Path
from graphqler import config
from graphqler.utils.file_utils import read_yaml_to_dict


class API:
    """Variables for the API"""

    queries = {}
    objects = {}
    mutations = {}
    input_objects = {}
    enums = {}
    unions = {}
    interfaces = {}

    def __init__(self, url: str = "http://localhost:4000/graphql", save_path: Path | str = "output/"):
        self.compiled_queries_save_path = Path(save_path) / config.COMPILED_QUERIES_FILE_NAME
        self.compiled_objects_save_path = Path(save_path) / config.COMPILED_OBJECTS_FILE_NAME
        self.compiled_mutations_save_path = Path(save_path) / config.COMPILED_MUTATIONS_FILE_NAME
        self.extracted_enums_save_path = Path(save_path) / config.ENUM_LIST_FILE_NAME
        self.extracted_input_objects_save_path = Path(save_path) / config.INPUT_OBJECT_LIST_FILE_NAME
        self.extracted_unions_save_path = Path(save_path) / config.UNION_LIST_FILE_NAME
        self.extracted_interfaces_save_path = Path(save_path) / config.INTERFACE_LIST_FILE_NAME

        self.url = url
        self.queries = read_yaml_to_dict(self.compiled_queries_save_path)
        self.objects = read_yaml_to_dict(self.compiled_objects_save_path)
        self.mutations = read_yaml_to_dict(self.compiled_mutations_save_path)
        self.input_objects = read_yaml_to_dict(self.extracted_input_objects_save_path)
        self.enums = read_yaml_to_dict(self.extracted_enums_save_path)
        self.unions = read_yaml_to_dict(self.extracted_unions_save_path)
        self.interfaces = read_yaml_to_dict(self.extracted_interfaces_save_path)

    def get_num_queries(self) -> int:
        """Gets the number of queries

        Returns:
            int: The number of queries
        """
        return len(self.queries.keys())

    def get_num_mutations(self) -> int:
        """Gets the number of mutations

        Returns:
            int: The number of mutations
        """
        return len(self.mutations.keys())

    def get_num_objects(self) -> int:
        """Gets the number of objects

        Returns:
            int: The number of objects
        """
        return len(self.objects.keys())

    def get_num_input_objects(self) -> int:
        """Gets the number of input objects

        Returns:
            int: The number of input objects
        """
        return len(self.input_objects.keys())

    def get_num_enums(self) -> int:
        """Gets the number of enums

        Returns:
            int: The number of enums
        """
        return len(self.enums.keys())

    def get_num_unions(self) -> int:
        """Gets the number of unions

        Returns:
            int: The number of unions
        """
        return len(self.unions.keys())

    def get_num_interfaces(self) -> int:
        """Gets the number of interfaces

        Returns:
            int: The number of interfaces
        """
        return len(self.interfaces.keys())

    def is_operation_in_api(self, operation: str) -> bool:
        """Checks if the operation is in the API

        Args:
            operation (str): The operation

        Returns:
            bool: True if the operation is in the API, False otherwise
        """
        return operation in self.queries or operation in self.mutations

    def get_operation(self, operation: str) -> dict:
        """Gets the operation from the API

        Args:
            operation (str): The operation

        Returns:
            dict: The operation
        """
        if operation in self.queries:
            return self.queries[operation]
        if operation in self.mutations:
            return self.mutations[operation]
        return {}
