"""Compiler class - responsible for:
- Getting the introspection query results into various files we can use later on
- Resolving dependencies among objects
- Tieing queries / mutations to objects
"""

from pathlib import Path
from graphqler.utils import plugins_handler
from graphqler.utils.file_utils import write_dict_to_yaml, write_json_to_file, initialize_file
from graphqler.utils.logging_utils import Logger
from .introspection_query import introspection_query
from .parsers import QueryListParser, ObjectListParser, MutationListParser, InputObjectListParser, EnumListParser, UnionListParser, InterfaceListParser, Parser
from .resolvers import ObjectDependencyResolver, ObjectMethodResolver, MutationObjectResolver, QueryObjectResolver
from graphqler import config
from clairvoyance.cli import blind_introspection

import asyncio
import json


class Compiler:
    def __init__(self, save_path: str, url: str):
        """Initializes the compiler,
            creates all necessary file paths to save the outputs for run if doesn't already exist

        Args:
            save_path (str): Save directory path
            url (str): URL for graphql introspection query to hit
        """
        self.save_path = save_path
        self.introspection_result_save_path = Path(save_path) / Path(config.INTROSPECTION_RESULT_FILE_NAME)
        self.object_list_save_path = Path(save_path) / config.OBJECT_LIST_FILE_NAME
        self.input_object_list_save_path = Path(save_path) / config.INPUT_OBJECT_LIST_FILE_NAME
        self.mutation_parameter_save_path = Path(save_path) / config.MUTATION_PARAMETER_FILE_NAME
        self.query_parameter_save_path = Path(save_path) / config.QUERY_PARAMETER_FILE_NAME
        self.enum_list_save_path = Path(save_path) / config.ENUM_LIST_FILE_NAME
        self.union_list_save_path = Path(save_path) / config.UNION_LIST_FILE_NAME
        self.interface_list_save_path = Path(save_path) / config.INTERFACE_LIST_FILE_NAME

        self.compiled_objects_save_path = Path(save_path) / config.COMPILED_OBJECTS_FILE_NAME
        self.compiled_mutations_save_path = Path(save_path) / config.COMPILED_MUTATIONS_FILE_NAME
        self.compiled_queries_save_path = Path(save_path) / config.COMPILED_QUERIES_FILE_NAME
        self.url = url

        # Initialize the parsers we will use
        self.object_list_parser = ObjectListParser()
        self.query_list_parser = QueryListParser()
        self.mutation_list_parser = MutationListParser()
        self.input_object_list_parser = InputObjectListParser()
        self.enum_list_parser = EnumListParser()
        self.union_list_parser = UnionListParser()
        self.interface_list_parser = InterfaceListParser()

        # Initialize the logger
        self.logger = Logger().get_compiler_logger()

        # Initialize the plugins handler to get request utils
        self.request_utils = plugins_handler.get_request_utils()

        # Create empty files for these files
        Path(self.save_path).mkdir(parents=True, exist_ok=True)
        initialize_file(self.introspection_result_save_path)
        initialize_file(self.object_list_save_path)
        initialize_file(self.input_object_list_save_path)
        initialize_file(self.mutation_parameter_save_path)
        initialize_file(self.query_parameter_save_path)
        initialize_file(self.enum_list_save_path)
        initialize_file(self.union_list_save_path)
        initialize_file(self.interface_list_save_path)
        initialize_file(self.compiled_objects_save_path)
        initialize_file(self.compiled_mutations_save_path)
        initialize_file(self.compiled_queries_save_path)

    def run(self):
        """The only function required to be run from the caller, will perform:
        1. Introspection query
        2. Trying clairvoyance if introspection query fails
        3. Run the parsers, storing files into objects / query / mutations
        4. Creating dependencies between objects and attaching methods (query/mutations) to objects
        """
        introspection_result = self.get_introspection_query_results()
        if introspection_result is None or introspection_result == {}:
            print("(C) Introspection query failed, trying clairvoyance")
            introspection_result = self.get_clairvoyance_results()

        if introspection_result is None or introspection_result == {}:
            raise SystemExit("(E) Couldn't get schema of the API. Exiting")

        self.run_parsers_and_save(introspection_result)
        self.run_resolvers_and_save(introspection_result)

    def get_introspection_query_results(self) -> dict:
        """Run the introspection query, grab results and output to file. Raises error if introspection query wasn't successful

        Returns:
            dict: Dictionary of the resulting JSON from the introspection query
        """
        result, response = self.request_utils.send_graphql_request(self.url, introspection_query)
        if "introspection is not allowed" in response.text.lower():
            self.logger.warning("GraphQL Introspection is not allowed")
            return {}
        elif "is not allowed" in response.text.lower():
            self.logger.warning("GraphQL Introspection is not allowed")
            return {}
        elif response.status_code != 200:
            error_message = f"Introspection query failed with status code {response.status_code}"
            self.logger.error(error_message)
            raise SystemExit(error_message)
        else:
            write_json_to_file(result, self.introspection_result_save_path)
            return result

    def get_clairvoyance_results(self) -> dict:
        """Runs clairvoyance to get an introspection query output

        Returns:
            dict: The introspection result using clairvoyance
        """
        wordlist = []
        if config.WORDLIST_PATH != "":
            with open(config.WORDLIST_PATH, "r") as file:
                wordlist = file.read().splitlines()

        schema_str = asyncio.run(
            blind_introspection(
                url=self.url,
                logger=self.logger,
                wordlist=wordlist,
                headers=self.request_utils.get_headers(),
                input_document=None,
                input_schema_path=None,
                output_path=str(self.introspection_result_save_path),
            )
        )
        schema = json.loads(schema_str)
        return schema

    def run_parsers_and_save(self, introspection_result: dict):
        """Runs all the parsers and saves them to a YAML file

        Args:
            introspection_result (dict): Introspection results as a dict
        """
        self.run_parser_and_save_list(self.object_list_parser, self.object_list_save_path, introspection_result)
        self.run_parser_and_save_list(self.query_list_parser, self.query_parameter_save_path, introspection_result)
        self.run_parser_and_save_list(self.mutation_list_parser, self.mutation_parameter_save_path, introspection_result)
        self.run_parser_and_save_list(self.input_object_list_parser, self.input_object_list_save_path, introspection_result)
        self.run_parser_and_save_list(self.enum_list_parser, self.enum_list_save_path, introspection_result)
        self.run_parser_and_save_list(self.union_list_parser, self.union_list_save_path, introspection_result)
        self.run_parser_and_save_list(self.interface_list_parser, self.interface_list_save_path, introspection_result)

    def run_parser_and_save_list(self, parser_instance: Parser, save_path: str | Path, introspection_result: dict):
        """Runs the given parser instance on the introspection result and saves to the save_path

        Args:
            parser_instance (Parser): Parser instance
            save_path (str): Path to save parsed results (in YAML format)
            introspection_result (dict): Introspection result as a dict
        """
        parsed_result = parser_instance.parse(introspection_result)
        write_dict_to_yaml(parsed_result, save_path)

    def run_resolvers_and_save(self, introspection_result: dict):
        """Resolves objects, mutations and queries together so make it a "compiled" look:
            1. Enriches object-object dependency
            2. Enriches object-method dependency
            3. Enriches mutation-object dependency
            4. Enriches query-object dependency
            5. Write enrichmend objects to "compiled" directory in a yaml file

        Args:
            introspection_result (dict): Introspection query result
        """
        objects = self.object_list_parser.parse(introspection_result)
        queries = self.query_list_parser.parse(introspection_result)
        mutations = self.mutation_list_parser.parse(introspection_result)
        input_objects = self.input_object_list_parser.parse(introspection_result)

        objects = ObjectDependencyResolver().resolve(objects)
        objects = ObjectMethodResolver().resolve(objects, queries, mutations)

        mutations = MutationObjectResolver().resolve(objects, mutations, input_objects)
        queries = QueryObjectResolver().resolve(objects, queries, input_objects)

        write_dict_to_yaml(objects, self.compiled_objects_save_path)
        write_dict_to_yaml(mutations, self.compiled_mutations_save_path)
        write_dict_to_yaml(queries, self.compiled_queries_save_path)
