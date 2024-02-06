from pathlib import Path
from graph import Node
from fuzzer.fengine.types import Result
from .singleton import singleton
from .file_utils import initialize_file

import constants
import pprint
import json
import time


@singleton
class Stats:
    ### PUT THE STATS YOU WANT HERE
    file_path = "/tmp/stats.txt"  # This gets overriden on startup
    start_time: float = 0
    end_time: float = 0
    http_status_codes: dict[str, dict[str, int]] = {}
    successful_nodes: dict[str, int] = {}
    external_failed_nodes: dict[str, int] = {}
    internal_failed_nodes: dict[str, int] = {}
    number_of_queries: int = 0
    number_of_mutations: int = 0
    number_of_objects: int = 0
    number_of_successes: int = 0
    number_of_failures: int = 0

    def __init__(self):
        self.http_status_codes = {}

    def add_new_succesful_node(self, node: Node):
        """Adds a new successful node to the succesful stats

        Args:
            node (Node): A graphqler node
        """
        key_name = f"{node.graphql_type}|{node.name}"
        if key_name in self.successful_nodes:
            self.successful_nodes[key_name] += 1
        else:
            self.successful_nodes[key_name] = 1
        self.save()

    def add_new_external_failed_node(self, node: Node):
        """Adds a new external failed node to the external failed stats

        Args:
            node (Node): A graphqler node
        """
        key_name = f"{node.graphql_type}|{node.name}"
        if key_name in self.external_failed_nodes:
            self.external_failed_nodes[key_name] += 1
        else:
            self.external_failed_nodes[key_name] = 1
        self.save()

    def add_new_internal_failed_node(self, node: Node):
        """Adds a new internal failed node to the internal failed stats

        Args:
            node (Node): A graphqler node
        """
        key_name = f"{node.graphql_type}|{node.name}"
        if key_name in self.internal_failed_nodes:
            self.internal_failed_nodes[key_name] += 1
        else:
            self.internal_failed_nodes[key_name] = 1
        self.save()

    def add_http_status_code(self, payload_name: str, status_code: int):
        """Adds the http status code to stats

        Args:
            payload_name (str): The name of the query or mutation
            status_code (int): The status code
        """
        if status_code in self.http_status_codes:
            if payload_name in self.http_status_codes[status_code]:
                self.http_status_codes[status_code][payload_name] += 1
            else:
                self.http_status_codes[status_code][payload_name] = 1
        else:
            self.http_status_codes[status_code] = {payload_name: 1}
        self.save()

    def set_file_path(self, working_dir: str):
        initialize_file(Path(working_dir) / constants.STATS_FILE_PATH)
        self.file_path = Path(working_dir) / constants.STATS_FILE_PATH

    def print_running_stats(self):
        """Function to print stats during runtime (not saved to file)"""
        print(f"Number of success: {self.number_of_successes}", end="")
        print("|", end="")
        print(f"Number of failures: {self.number_of_failures}", end="")
        print("\r", end="", flush=True)

    def get_number_of_successful_mutations_and_queries(self) -> tuple[int, int]:
        """Returns the number of successful mutations and queries"""
        number_success_of_mutations_and_queries = 0
        num_mutations_and_queries = self.number_of_mutations + self.number_of_queries
        for action, num_success in self.successful_nodes.items():
            action_name = action.split("|")[0]
            if action_name == "Mutation" or action_name == "Query":
                if num_success > 0:
                    number_success_of_mutations_and_queries += 1
        return number_success_of_mutations_and_queries, num_mutations_and_queries

    def update_stats_from_result(self, node, result: Result) -> None:
        """Parses the result and adds it to the stats

        Args:
            result (Result): the result
        """
        if result == Result.EXTERNAL_FAILURE:
            self.add_new_external_failed_node(node)
        elif result == Result.INTERNAL_FAILURE:
            self.add_new_internal_failed_node(node)
        elif result == Result.GENERAL_SUCCESS:
            self.add_new_succesful_node(node)

    def get_number_of_failed_external_mutations_and_queries(self) -> tuple[int, int]:
        """Returns the number of failed EXTERNAL mutations and queries"""
        number_failed_of_mutations_and_queries = 0
        num_mutations_and_queries = self.number_of_mutations + self.number_of_queries
        for action, num_failed in self.external_failed_nodes.items():
            action_name = action.split("|")[0]
            if action_name == "Mutation" or action_name == "Query":
                if num_failed > 0:
                    number_failed_of_mutations_and_queries += 1
        return number_failed_of_mutations_and_queries, num_mutations_and_queries

    def print_results(self):
        print("\n----------------------RESULTS-------------------------")
        print("Unique success nodes:")
        pprint.pprint(self.successful_nodes)
        print("Unique external failed nodes:")
        pprint.pprint(self.external_failed_nodes)
        print("Unique internal failed nodes")
        pprint.pprint(self.internal_failed_nodes)
        number_success_of_mutations_and_queries, num_mutations_and_queries = self.get_number_of_successful_mutations_and_queries()
        number_failed_of_mutations_and_queries, num_mutations_and_queries = self.get_number_of_failed_external_mutations_and_queries()
        print(f"(RESULTS): Time taken: {self.end_time - self.start_time} seconds")
        print(f"(RESULTS): Number of queries: {self.number_of_queries}")
        print(f"(RESULTS): Number of mutations: {self.number_of_mutations}")
        print(f"(RESULTS): Number of objects: {self.number_of_objects}")
        print(f"(RESULTS): Number of unique query/mutation successes: {number_success_of_mutations_and_queries}/{num_mutations_and_queries}")
        print(f"(RESULTS): Number of unique external query/mutation failures: {number_failed_of_mutations_and_queries}/{num_mutations_and_queries}")
        print(f"(RESULTS): Please check {self.file_path} for more information regarding the run")
        print("------------------------------------------------------")

    def save(self):
        number_success_of_mutations_and_queries, num_mutations_and_queries = self.get_number_of_successful_mutations_and_queries()
        number_failed_of_mutations_and_queries, num_mutations_and_queries = self.get_number_of_failed_external_mutations_and_queries()
        with open(self.file_path, "w") as f:
            f.write("\n===================HTTP Status Codes===================\n")
            f.write(json.dumps(self.http_status_codes, indent=4))
            f.write("\n===================Successful Nodes===================\n")
            f.write(json.dumps(self.successful_nodes, indent=4))
            f.write("\n===================External failed Nodes===================\n")
            f.write(json.dumps(self.external_failed_nodes, indent=4))
            f.write("\n===================Internal failed Nodes===================\n")
            f.write(json.dumps(self.internal_failed_nodes, indent=4))
            f.write("\n===================General stats ===================\n")
            f.write(f"\nTime taken: {str(self.end_time - self.start_time)} seconds")
            f.write(f"\nNumber of unique query/mutation successes: {number_success_of_mutations_and_queries}/{num_mutations_and_queries}")
            f.write(f"\nNumber of unique external query/mutation failures: {number_failed_of_mutations_and_queries}/{num_mutations_and_queries}")
            f.write(f"\nNumber of queries: {self.number_of_queries}")
            f.write(f"\nNumber of mutations: {self.number_of_mutations}")
            f.write(f"\nNumber of objects: {self.number_of_objects}")
            f.write(f"\nNumber of successes: {self.number_of_successes}")
            f.write(f"\nNumber of failures: {self.number_of_failures}")
