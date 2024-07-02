from pathlib import Path
from graphqler.graph import Node
from graphqler.fuzzer.fengine.types import Result
from .singleton import singleton
from .file_utils import initialize_file

from graphqler import constants
import pprint
import json
import time


@singleton
class Stats:
    ### PUT THE STATS YOU WANT HERE
    file_path = "/tmp/stats.txt"  # This gets overriden on startup
    start_time: float = 0
    http_status_codes: dict[str, dict[str, int]] = {}
    successful_nodes: dict[str, int] = {}
    failed_nodes: dict[str, int] = {}
    results: dict[str, dict[str, int]] = {}
    number_of_queries: int = 0
    number_of_mutations: int = 0
    number_of_objects: int = 0
    number_of_successes: int = 0
    number_of_failures: int = 0

    def __init__(self):
        self.http_status_codes = {}

    def add_successful_node(self, node: Node):
        """Adds a new successful node to the succesful stats

        Args:
            node (Node): A graphqler node
        """
        key_name = f"{node.graphql_type}|{node.name}"
        self.number_of_successes += 1
        if key_name in self.successful_nodes:
            self.successful_nodes[key_name] += 1
        else:
            self.successful_nodes[key_name] = 1
        self.save()

    def add_failed_node(self, node: Node):
        """Adds a new failed node to the internal failed stats

        Args:
            node (Node): A graphqler node
        """
        key_name = f"{node.graphql_type}|{node.name}"
        self.number_of_failures += 1
        if key_name in self.failed_nodes:
            self.failed_nodes[key_name] += 1
        else:
            self.failed_nodes[key_name] = 1
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

    def update_stats_from_result(self, node, result: Result) -> None:
        """Parses the result and adds it to the stats

        Args:
            result (Result): the result
        """
        result_status = result.get_success()
        result_type = result.get_type()

        # Update success / fail stats first
        if result_status:
            self.add_successful_node(node)
        else:
            self.add_failed_node(node)

        # Update results
        if result_type in self.results and node.name in self.results[result_type]:
            self.results[result_type][node.name] += 1
        elif result_type in self.results and node.name not in self.results[result_type]:
            self.results[result_type][node.name] = 1
        else:
            self.results[result_type] = {node.name: 1}

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

    def get_number_of_failed_mutations_and_queries(self) -> tuple[int, int]:
        """Returns the number of failed EXTERNAL mutations and queries"""
        number_failed_of_mutations_and_queries = 0
        num_mutations_and_queries = self.number_of_mutations + self.number_of_queries
        for action, num_failed in self.failed_nodes.items():
            action_name = action.split("|")[0]
            if action_name == "Mutation" or action_name == "Query":
                if num_failed > 0:
                    number_failed_of_mutations_and_queries += 1
        return number_failed_of_mutations_and_queries, num_mutations_and_queries

    def print_results(self):
        print("\n----------------------RESULTS-------------------------")
        print("Unique success nodes:")
        pprint.pprint(self.successful_nodes)
        print("Unique failed nodes:")
        pprint.pprint(self.failed_nodes)
        number_success_of_mutations_and_queries, num_mutations_and_queries = self.get_number_of_successful_mutations_and_queries()
        number_failed_of_mutations_and_queries, num_mutations_and_queries = self.get_number_of_failed_mutations_and_queries()
        print(f"(RESULTS): Time taken: {time.time() - self.start_time} seconds")
        print(f"(RESULTS): Number of queries: {self.number_of_queries}")
        print(f"(RESULTS): Number of mutations: {self.number_of_mutations}")
        print(f"(RESULTS): Number of objects: {self.number_of_objects}")
        print(f"(RESULTS): Number of unique query/mutation successes: {number_success_of_mutations_and_queries}/{num_mutations_and_queries}")
        print(f"(RESULTS): Number of unique external query/mutation failures: {number_failed_of_mutations_and_queries}/{num_mutations_and_queries}")
        print(f"(RESULTS): Please check {self.file_path} for more information regarding the run")
        print("------------------------------------------------------")

    def save(self):
        number_success_of_mutations_and_queries, num_mutations_and_queries = self.get_number_of_successful_mutations_and_queries()
        number_failed_of_mutations_and_queries, num_mutations_and_queries = self.get_number_of_failed_mutations_and_queries()
        with open(self.file_path, "w") as f:
            f.write("\n===================HTTP Status Codes===================\n")
            f.write(json.dumps(self.http_status_codes, indent=4))
            f.write("\n===================Successful Nodes===================\n")
            f.write(json.dumps(self.successful_nodes, indent=4))
            f.write("\n===================Failed Nodes===================\n")
            f.write(json.dumps(self.failed_nodes, indent=4))
            f.write("\n===================Results===================\n")
            f.write(json.dumps(self.results, indent=4))
            f.write("\n===================General stats ===================\n")
            f.write(f"\nTime taken: {str(time.time() - self.start_time)} seconds")
            f.write(f"\nNumber of unique query/mutation successes: {number_success_of_mutations_and_queries}/{num_mutations_and_queries}")
            f.write(f"\nNumber of unique external query/mutation failures: {number_failed_of_mutations_and_queries}/{num_mutations_and_queries}")
            f.write(f"\nNumber of queries: {self.number_of_queries}")
            f.write(f"\nNumber of mutations: {self.number_of_mutations}")
            f.write(f"\nNumber of objects: {self.number_of_objects}")
            f.write(f"\nNumber of successes: {self.number_of_successes}")
            f.write(f"\nNumber of failures: {self.number_of_failures}")
