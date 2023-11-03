from pathlib import Path
from .singleton import singleton
from .file_utils import initialize_file
from graph import Node

import constants
import pprint
import json


@singleton
class Stats:
    ### PUT THE STATS YOU WANT HERE
    file_path = "/tmp/stats.txt"  # This gets overriden on startup
    http_status_codes: dict[str, dict[str, int]] = {}
    successful_nodes: dict[str, int] = {}
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

    def print_results(self):
        print("\n----------------------RESULTS-------------------------")
        pprint.pprint(self.successful_nodes)
        number_success_of_mutations_and_queries = 0
        num_mutations_and_queries = self.number_of_mutations + self.number_of_queries
        for action, num_success in self.successful_nodes.items():
            action_name = action.split("|")[0]
            if action_name == "Mutation" or action_name == "Query":
                if num_success > 0:
                    number_success_of_mutations_and_queries += 1
        print(f"(RESULTS): Number of queries: {self.number_of_queries}")
        print(f"(RESULTS): Number of mutations: {self.number_of_mutations}")
        print(f"(RESULTS): Number of objects: {self.number_of_objects}")
        print(f"(RESULTS): Number of unique QUERY/mutation successes: {number_success_of_mutations_and_queries}/{num_mutations_and_queries}")
        print(f"(RESULTS): Please check {self.file_path} for more information regarding the run")
        print("------------------------------------------------------")

    def save(self):
        with open(self.file_path, "w") as f:
            f.write("\n===================HTTP Status Codes===================\n")
            f.write(json.dumps(self.http_status_codes, indent=4))
            f.write("\n===================Successful Nodes===================\n")
            f.write(json.dumps(self.successful_nodes, indent=4))
            f.write("\n===================General stats ===================\n")
            f.write(f"\nNumber of queries: {self.number_of_queries}")
            f.write(f"\nNumber of mutations: {self.number_of_mutations}")
            f.write(f"\nNumber of objects: {self.number_of_objects}")
            f.write(f"\nNumber of successes: {self.number_of_successes}")
            f.write(f"\nNumber of failures: {self.number_of_failures}")
