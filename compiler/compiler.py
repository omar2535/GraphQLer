"""Compiler class - responsible for compiling the introspection query results into various files we can use later on
"""

from pathlib import Path
from utils.utils import send_graphql_request
from compiler.introspection_query import introspection_query

import constants
import requests


class Compiler:
    def __init__(self, save_path: str, url: str):
        """Initializes the compiler,
           creates all necessary file paths for run if doesn't already exist

        Args:
            save_path (str): Save directory path
            url (str): URL for graphql introspection query to hit
        """
        Path(save_path).mkdir(parents=True, exist_ok=True)
        open(Path(save_path) / constants.FUNCTION_LIST_FILE_NAME, "a").close()
        open(Path(save_path) / constants.MUTATION_PARAMETER_FILE_NAME, "a").close()
        open(Path(save_path) / constants.QUERY_PARAMETER_FILE_NAME, "a").close()
        open(Path(save_path) / constants.SCHEMA_FILE_NAME, "a").close()

        self.path = save_path
        self.url = url

    def run(self):
        """The only function required to be run from the caller, will perform:
        1. Introspection query running
        2. Parsing through results
        3. Storing files into query / mutations
        """
        self.get_introspection_query()

    def get_introspection_query(self):
        """Run the introspection query, grab results and output to file"""
        send_graphql_request(self.url, introspection_query)
        # breakpoint()
