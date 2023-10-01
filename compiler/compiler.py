"""Compiler class - responsible for:
    - Getting the introspection query results into various files we can use later on
    - Resolving dependencies among objects
    - Tieing queries / mutations to objects
"""

from pathlib import Path
from compiler.utils import send_graphql_request, write_json_to_file
from compiler.introspection_query import introspection_query
from compiler.parsers import QueryListParser, ObjectListParser, MutationListParser, Parser
from compiler.resolvers import ObjectDepdenencyResolver

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
        self.introspection_result = self.get_introspection_query()

        self.run_parser_and_save_list(ObjectListParser(), self.object_list_save_path)
        self.run_parser_and_save_list(QueryListParser(), self.query_parameter_save_path)
        self.run_parser_and_save_list(MutationListParser(), self.mutation_parameter_save_path)

        self.run_object_dependency_resolver_and_save()

    def get_introspection_query(self) -> dict:
        """Run the introspection query, grab results and output to file

        Returns:
            dict: Dictionary of the resulting JSON from the introspection query
        """
        result = send_graphql_request(self.url, introspection_query)
        write_json_to_file(result, self.introspection_result_save_path)
        return result

    def run_parser_and_save_list(self, parser_instance: Parser, save_path: str):
        """Runs the given parser instance and saves to the save_path

        Args:
            parser_instance (Parser): Parser instance
            save_path (str): Path to save parsed results (in YAML format)
        """
        parsed_list = parser_instance.parse(self.introspection_result)
        yaml_data = yaml.dump(parsed_list, default_flow_style=False)
        with open(save_path, "w") as yaml_file:
            yaml_file.write(yaml_data)

    def run_object_dependency_resolver_and_save(self):
        objects = ObjectListParser().parse(self.introspection_result)
        object_dependency_resolver = ObjectDepdenencyResolver(objects)
        self.resolved_objects = object_dependency_resolver.resolve()
