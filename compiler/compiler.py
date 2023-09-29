"""Compiler class - responsible for compiling the introspection query results into various files we can use later on
"""

from pathlib import Path
from compiler.utils import send_graphql_request, write_json_to_file
from compiler.introspection_query import introspection_query
from compiler.parsers.object_list_parser import ObjectListParser

import constants
import yaml


class Compiler:
    def __init__(self, save_path: str, url: str):
        """Initializes the compiler,
            creates all necessary file paths to save the outputs for run if doesn't already exist

        Args:
            save_path (str): Save directory path
            url (str): URL for graphql introspection query to hit
        """
        self.save_path = save_path
        self.introspection_result_save_path = Path(save_path) / constants.INTROSPECTION_RESULT_FILE_NAME
        self.function_list_save_path = Path(save_path) / constants.FUNCTION_LIST_FILE_NAME
        self.object_list_save_path = Path(save_path) / constants.OBJECT_LIST_FILE_NAME
        self.mutation_parameter_save_path = Path(save_path) / constants.MUTATION_PARAMETER_FILE_NAME
        self.query_parameter_save_path = Path(save_path) / constants.QUERY_PARAMETER_FILE_NAME
        self.schema_save_path = Path(save_path) / constants.SCHEMA_FILE_NAME
        self.url = url

        Path(self.save_path).mkdir(parents=True, exist_ok=True)
        open(self.introspection_result_save_path, "a").close()
        open(self.function_list_save_path, "a").close()
        open(self.object_list_save_path, "a").close()
        open(self.mutation_parameter_save_path, "a").close()
        open(self.query_parameter_save_path, "a").close()
        open(self.schema_save_path, "a").close()

    def run(self):
        """The only function required to be run from the caller, will perform:
        1. Introspection query running
        2. Parsing through results
        3. Storing files into query / mutations
        """
        introspection_result = self.get_introspection_query()
        self.parse_and_save_object_list(introspection_result)

    def get_introspection_query(self) -> dict:
        """Run the introspection query, grab results and output to file

        Returns:
            dict: Dictionary of the resulting JSON from the introspection query
        """
        result = send_graphql_request(self.url, introspection_query)
        write_json_to_file(result, self.introspection_result_save_path)
        return result

    def parse_and_save_object_list(self, introspection_result: dict):
        """Parse and save the object list from the introspection query result dictionary

        Args:
            introspection_result (dict): Introspection query result as a dictionary
        """
        object_list_parser_instance = ObjectListParser()
        parsed_object_list = object_list_parser_instance.parse(introspection_result)
        yaml_data = yaml.dump(parsed_object_list, default_flow_style=False)
        with open(self.object_list_save_path, "w") as yaml_file:
            yaml_file.write(yaml_data)
