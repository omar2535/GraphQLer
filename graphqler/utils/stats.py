import json
import cloudpickle as pickle
import pprint
import time
from pathlib import Path
from typing import Self

from graphqler import config
from graphqler.fuzzer.engine.types import Result
from graphqler.graph import Node

from .file_utils import initialize_file, intialize_file_if_not_exists, recreate_path, get_or_create_file
from .singleton import singleton


@singleton
class Stats :
    ### PUT THE STATS YOU WANT HERE
    file_path = "/tmp/stats.txt"  # This gets overriden by the set_file_path function
    endpoint_results_dir = "/tmp/endpoint_results"
    unique_responses_file_path = "/tmp/unique_responses.txt"
    start_time: float = 0
    http_status_codes: dict[str, dict[str, int]] = {}
    successful_nodes: dict[str, int] = {}
    failed_nodes: dict[str, int] = {}
    results: dict[str, set[Result]] = {}    # Mapping of query/muation to results for that node
    unique_responses: dict[str, list[str]] = {}  # Mapping of response to endpoints (query/mutation)
    number_of_queries: int = 0
    number_of_mutations: int = 0
    number_of_objects: int = 0
    number_of_successes: int = 0
    number_of_failures: int = 0
    vulnerabilities = {}  # Mapping of vulnerability to node name, and if it's a potentiall or confirmed vulnerability

    # Detection stats
    is_introspection_available: bool = False

    def __init__(self):
        self.http_status_codes = {}
        self.pickle_save_path = Path(config.OUTPUT_DIRECTORY) / config.SERIALIZED_DIR_NAME / config.STATS_PICKLE_FILE_NAME

    def load(self) -> Self:
        """Loads the stats from the pickle file"""
        self.__load_pickle()
        return self

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
        status_code_str = str(status_code)
        if status_code_str in self.http_status_codes.keys():
            if payload_name in self.http_status_codes[status_code_str]:
                self.http_status_codes[status_code_str][payload_name] += 1
            else:
                self.http_status_codes[status_code_str][payload_name] = 1
        else:
            self.http_status_codes[status_code_str] = {payload_name: 1}
        self.save()

    def set_file_paths(self, working_dir: str):
        """

        Args:
            working_dir (str): _description_
        """
        # Do the stats file first
        initialize_file(Path(working_dir) / config.STATS_FILE_NAME)
        self.file_path = Path(working_dir) / config.STATS_FILE_NAME

        # Do the endpoint results directory
        self.endpoint_results_dir = Path(working_dir) / config.ENDPOINT_RESULTS_DIR_NAME
        recreate_path(self.endpoint_results_dir)

        # Do the unique responses file
        self.unique_responses_file_path = Path(working_dir) / config.UNIQUE_RESPONSES_FILE_NAME
        initialize_file(self.unique_responses_file_path)

    def print_running_stats(self):
        """Function to print stats during runtime (not saved to file)"""
        print(f"Number of success: {self.number_of_successes}", end="")
        print("|", end="")
        print(f"Number of failures: {self.number_of_failures}", end="")
        print("\r", end="", flush=True)

    def add_vulnerability(self, vulnerability_name: str, node_name: str, is_vulnerable: bool, potentially_vulnerable: bool = False):
        """Whether a detection was detected or not -- if already detected, it will stay detected

        Args:
            detection_name (str): name of the detection
            detected (bool): whether the detection was detected or not
        """
        if vulnerability_name not in self.vulnerabilities:
            self.vulnerabilities[vulnerability_name] = {}

        if node_name in self.vulnerabilities[vulnerability_name]:
            self.vulnerabilities[vulnerability_name][node_name]["potentially_vulnerable"] = (
                potentially_vulnerable | self.vulnerabilities[vulnerability_name][node_name]["potentially_vulnerable"]
            )
            self.vulnerabilities[vulnerability_name][node_name]["is_vulnerable"] = is_vulnerable | self.vulnerabilities[vulnerability_name][node_name]["is_vulnerable"]
        else:
            self.vulnerabilities[vulnerability_name][node_name] = {}
            self.vulnerabilities[vulnerability_name][node_name]["potentially_vulnerable"] = potentially_vulnerable
            self.vulnerabilities[vulnerability_name][node_name]["is_vulnerable"] = is_vulnerable

    def get_formatted_vulnerabilites(self) -> str:
        """Returns the formatted vulnerabilities

        Returns:
            str: The formatted vulnerabilities
        """
        formatted_vulnerabilities = ""
        for vulnerability_name, nodes in self.vulnerabilities.items():
            vulnerable_nodes = ""
            for node_name, vulnerability in nodes.items():
                if vulnerability["is_vulnerable"] or vulnerability["potentially_vulnerable"]:
                    if vulnerability["is_vulnerable"]:
                        vulnerable_nodes += f"  ❗'{node_name}'  - Is vulnerable\n"
                    else:
                        vulnerable_nodes += f"  🔍'{node_name}'  - Is potentially vulnerable \n"
            if vulnerable_nodes != "":
                formatted_vulnerabilities += f"\n{vulnerability_name}:\n"
                formatted_vulnerabilities += vulnerable_nodes
        return formatted_vulnerabilities

    def update_stats_from_result(self, node, result: Result) -> None:
        """Parses the result and adds it to the stats

        Args:
            result (Result): the result
        """
        result_status = result.success

        # Update success / fail stats first
        if result_status:
            self.add_successful_node(node)
        else:
            self.add_failed_node(node)

        # Update results
        if node.name in self.results:
            self.results[node.name].add(result)
        else:
            self.results[node.name] = {result}

        # Update unique responses
        if str(result.graphql_response) in self.unique_responses:
            self.unique_responses[str(result.graphql_response)].append(node.name)
        else:
            self.unique_responses[str(result.graphql_response)] = [node.name]

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
        if len(self.vulnerabilities) > 0:
            print("----------------------DETECTED VULNS-------------------------")
            print(self.get_formatted_vulnerabilites())
        print("---------------------------------------------------------")

    def save(self):
        """Saves the stats into the stats text file
        """
        number_success_of_mutations_and_queries, num_mutations_and_queries = self.get_number_of_successful_mutations_and_queries()
        number_failed_of_mutations_and_queries, num_mutations_and_queries = self.get_number_of_failed_mutations_and_queries()
        with open(self.file_path, "w") as f:
            f.write("\n===================HTTP Status Codes===================\n")
            f.write(json.dumps(self.http_status_codes, indent=4))
            f.write("\n===================Successful Nodes===================\n")
            f.write(json.dumps(self.successful_nodes, indent=4))
            f.write("\n===================Failed Nodes===================\n")
            f.write(json.dumps(self.failed_nodes, indent=4))
            f.write("\n===================General stats ===================\n")
            f.write(f"\nTime taken: {str(time.time() - self.start_time)} seconds")
            f.write(f"\nNumber of unique query/mutation successes: {number_success_of_mutations_and_queries}/{num_mutations_and_queries}")
            f.write(f"\nNumber of unique external query/mutation failures: {number_failed_of_mutations_and_queries}/{num_mutations_and_queries}")
            f.write(f"\nNumber of queries: {self.number_of_queries}")
            f.write(f"\nNumber of mutations: {self.number_of_mutations}")
            f.write(f"\nNumber of objects: {self.number_of_objects}")
            f.write(f"\nNumber of successes: {self.number_of_successes}")
            f.write(f"\nNumber of failures: {self.number_of_failures}")
            if len(self.vulnerabilities) > 0:
                f.write("\n===================Detected Vulnerabilities===================\n")
                f.write(json.dumps(self.vulnerabilities, indent=4))
        self.save_endpoint_results()
        self.save_unique_response()

        # Saves the pickle file as well
        self.__save_pickle()

    def save_endpoint_results(self):
        """Reads the results, for each node in the node name -> results, create a directory for the
           result type, then a file for the response code, and append the payload and the response to the file.
        """
        unique_results = {}
        # Filter out for only unique results
        for node_name, results in self.results.items():
            # If the node name has slashes, replace them with underscores
            node_name = node_name.replace("/", "_")
            for result in results:
                result_type = "success" if result.success else "failure"
                result_file_path = Path(self.endpoint_results_dir) / node_name / result_type / f"{result.status_code}"

                payload_string = str(result.payload)
                if result_file_path not in unique_results:
                    unique_results[result_file_path] = {payload_string: result.graphql_response}
                else:
                    if payload_string not in unique_results[result_file_path]:
                        unique_results[result_file_path][payload_string] = result.graphql_response

        # Write the unique results to the file
        for result_file_path, payloads in unique_results.items():
            intialize_file_if_not_exists(result_file_path)
            for payload, response in payloads.items():
                with open(result_file_path, "a") as f:
                    f.write("------------------Payload:-------------------\n")
                    f.write(f"{payload}\n")
                    f.write("------------------Response:-------------------\n")
                    f.write(f"{response}\n")

    def save_unique_response(self):
        """Saves the unique responses to a file"""
        with open(Path(self.unique_responses_file_path), "w") as f:
            for response, endpoints in self.unique_responses.items():
                f.write(f"Response: {response}\n")
                f.write(f"Endpoints: {endpoints}\n")

    def __save_pickle(self):
        """Saves the stats to a pickle file"""
        self.pickle_save_path = get_or_create_file(self.pickle_save_path)
        with open(self.pickle_save_path, "wb") as file:
            pickle.dump(self, file)

    def __load_pickle(self):
        """Loads the stats from a pickle file"""
        if self.pickle_save_path.exists():
            with open(self.pickle_save_path, "rb") as file:
                loaded_stats = pickle.load(file)
                self.__dict__.update(loaded_stats.__dict__)
