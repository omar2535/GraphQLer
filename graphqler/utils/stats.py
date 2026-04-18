import json
import cloudpickle as pickle
import pprint
import shutil
import sys
import time
from pathlib import Path
from typing import Self

from graphqler import config
from graphqler.fuzzer.engine.types import Result
from graphqler.graph import Node

from .file_utils import initialize_file, intialize_file_if_not_exists, recreate_path, get_or_create_file
from .singleton import singleton
import os
import re


@singleton
class Stats :
    ### PUT THE STATS YOU WANT HERE
    file_path = "/tmp/stats.txt"  # This gets overriden by the set_file_path function
    endpoint_results_dir = "/tmp/endpoint_results"
    unique_responses_file_path = "/tmp/unique_responses.txt"
    start_time: float = 0.0
    http_status_codes: dict[str, dict[str, int]] = {}
    successful_nodes: dict[str, int] = {}
    failed_nodes: dict[str, int] = {}
    results: dict[str, set[Result]] = {}    # Mapping of query/mutation to results for that node
    unique_responses: dict[str, list[str]] = {}  # Mapping of response to endpoints (query/mutation)
    number_of_queries: int = 0
    number_of_mutations: int = 0
    number_of_objects: int = 0
    number_of_successes: int = 0
    number_of_failures: int = 0
    vulnerabilities = {}  # Mapping of vulnerability to node name, and if it's a potential or confirmed vulnerability
    node_timings: dict[str, list[float]] = {}  # Mapping of node name to list of elapsed times in seconds

    # Chain progress tracking
    chains_total: int = 0
    chains_completed: int = 0
    current_iteration: int = 1
    total_iterations: int = 1

    # Phase tracking ("chains" | "islands" | "detections")
    phase: str = "chains"
    islands_total: int = 0
    islands_completed: int = 0

    # Detection stats
    is_introspection_available: bool = False

    def __init__(self):
        self.start_time = time.time()
        self.http_status_codes = {}
        self.successful_nodes = {}
        self.failed_nodes = {}
        self.results = {}
        self.unique_responses = {}
        self.number_of_queries = 0
        self.number_of_mutations = 0
        self.number_of_objects = 0
        self.number_of_successes = 0
        self.number_of_failures = 0
        self.vulnerabilities = {}
        self.node_timings = {}
        self.is_introspection_available = False
        self.chains_total = 0
        self.chains_completed = 0
        self.current_iteration = 1
        self.total_iterations = 1
        self.phase = "chains"
        self.islands_total = 0
        self.islands_completed = 0
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

    def add_http_status_code(self, payload_name: str, status_code: int | None):
        """Adds the http status code to stats

        Args:
            payload_name (str): The name of the query or mutation
            status_code (int): The status code
        """
        if status_code is None:
            return
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

        # JSON report path (machine-readable)
        json_file_name = config.STATS_FILE_NAME.replace(".txt", ".json") if config.STATS_FILE_NAME.endswith(".txt") else config.STATS_FILE_NAME + ".json"
        initialize_file(Path(working_dir) / json_file_name)
        self.json_file_path = Path(working_dir) / json_file_name

        # Eval/ablation directory (written only when ablation flags are active)
        self.eval_dir = Path(working_dir) / config.EVAL_DIR_NAME

        # Do the endpoint results directory
        self.endpoint_results_dir = Path(working_dir) / config.ENDPOINT_RESULTS_DIR_NAME
        recreate_path(self.endpoint_results_dir)

        # Do the unique responses file
        self.unique_responses_file_path = Path(working_dir) / config.UNIQUE_RESPONSES_FILE_NAME
        initialize_file(self.unique_responses_file_path)

    def print_running_stats(self):
        """Print a single-line progress update that overwrites itself each second."""
        elapsed = time.time() - self.start_time
        elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
        counts = f"✓ {self.number_of_successes} | ✗ {self.number_of_failures}"

        if self.phase == "detections":
            progress = f"[Detections] {counts} | {elapsed_str} elapsed"
        elif self.phase == "islands":
            progress = (
                f"[Islands {self.islands_completed}/{self.islands_total}] "
                f"{counts} | {elapsed_str} elapsed"
            )
        elif self.chains_total > 0:
            overall_done = (self.current_iteration - 1) * self.chains_total + self.chains_completed
            overall_total = self.total_iterations * self.chains_total
            # Only show ETA once we have enough samples to make a reasonable estimate
            if overall_done >= 3 and elapsed > 0:
                eta_secs = (elapsed / overall_done) * (overall_total - overall_done)
                eta_str = time.strftime("%H:%M:%S", time.gmtime(eta_secs))
            else:
                eta_str = "--:--:--"
            progress = (
                f"[Iter {self.current_iteration}/{self.total_iterations} | "
                f"Chain {self.chains_completed}/{self.chains_total}] "
                f"{counts} | "
                f"{elapsed_str} elapsed | ETA {eta_str}"
            )
        else:
            progress = f"{counts} | {elapsed_str} elapsed"

        if not sys.stdout.isatty():
            return
        # Truncate to terminal width - 1 to prevent wrapping (wrapping breaks \r overwrite)
        term_cols = shutil.get_terminal_size((80, 24)).columns
        progress = progress[: term_cols - 1]
        # \r returns to line start; \x1b[K erases to end-of-line — no leftover ghosting
        print(f"\r\x1b[K{progress}", end="", flush=True)

    def add_vulnerability(
        self,
        vulnerability_name: str,
        node_name: str,
        is_vulnerable: bool,
        potentially_vulnerable: bool = False,
        payload: str = "",
        evidence: str = "",
    ):
        """Record a vulnerability finding.  Once a node is confirmed vulnerable it stays confirmed.

        Args:
            vulnerability_name (str): Name of the detector / vulnerability class.
            node_name (str): The GraphQL operation that triggered the finding.
            is_vulnerable (bool): True when vulnerability-specific evidence was observed (CONFIRMED).
            potentially_vulnerable (bool): True when only a generic indicator was observed (POTENTIAL).
            payload (str): The exact GraphQL payload that triggered the finding.
            evidence (str): Human-readable description of what specific indicator was matched,
                e.g. "matched SQL error pattern: 'sql syntax'".  Empty string means not yet determined.
        """
        if vulnerability_name not in self.vulnerabilities:
            self.vulnerabilities[vulnerability_name] = {}

        if node_name in self.vulnerabilities[vulnerability_name]:
            existing = self.vulnerabilities[vulnerability_name][node_name]
            existing["potentially_vulnerable"] = potentially_vulnerable | existing["potentially_vulnerable"]
            existing["is_vulnerable"] = is_vulnerable | existing["is_vulnerable"]
            # Prefer the confirmed finding's payload/evidence over a potential one
            if is_vulnerable or (not existing["is_vulnerable"] and potentially_vulnerable):
                if payload:
                    existing["payload"] = payload
                if evidence:
                    existing["evidence"] = evidence
        else:
            self.vulnerabilities[vulnerability_name][node_name] = {
                "potentially_vulnerable": potentially_vulnerable,
                "is_vulnerable": is_vulnerable,
                "payload": payload,
                "evidence": evidence,
            }

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
                    evidence_str = f" [{vulnerability.get('evidence', '')}]" if vulnerability.get("evidence") else ""
                    if vulnerability["is_vulnerable"]:
                        vulnerable_nodes += f"  ❗'{node_name}'  - Is vulnerable{evidence_str}\n"
                    else:
                        vulnerable_nodes += f"  🔍'{node_name}'  - Is potentially vulnerable{evidence_str}\n"
            if vulnerable_nodes != "":
                formatted_vulnerabilities += f"\n{vulnerability_name}:\n"
                formatted_vulnerabilities += vulnerable_nodes
        return formatted_vulnerabilities

    def get_coverage_rate(self) -> tuple[int, int, float]:
        """Returns (covered_operations, total_operations, coverage_fraction).

        A covered operation is one that returned at least one successful response
        (HTTP 200 with no GraphQL 'errors' field).
        """
        covered, total = self.get_number_of_successful_mutations_and_queries()
        fraction = covered / total if total > 0 else 0.0
        return covered, total, fraction

    def get_negative_coverage_rate(self) -> tuple[int, int, float]:
        """Returns (failed_operations, total_operations, negative_fraction).

        A negatively-covered operation is one that returned at least one failed response
        (any non-success result including GraphQL 'errors').
        """
        failed, total = self.get_number_of_failed_mutations_and_queries()
        fraction = failed / total if total > 0 else 0.0
        return failed, total, fraction

    def record_node_timing(self, node: Node, elapsed_seconds: float):
        """Records the elapsed time for a node execution

        Args:
            node (Node): The node that was executed
            elapsed_seconds (float): Time taken in seconds
        """
        key_name = f"{node.graphql_type}|{node.name}"
        if key_name not in self.node_timings:
            self.node_timings[key_name] = []
        self.node_timings[key_name].append(elapsed_seconds)

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
        covered, total, coverage_frac = self.get_coverage_rate()
        failed, _, negative_frac = self.get_negative_coverage_rate()
        print(f"(RESULTS): Time taken: {time.time() - self.start_time} seconds")
        print(f"(RESULTS): Number of queries: {self.number_of_queries}")
        print(f"(RESULTS): Number of mutations: {self.number_of_mutations}")
        print(f"(RESULTS): Number of objects: {self.number_of_objects}")
        print(f"(RESULTS): Operation coverage (successful):  {covered}/{total} ({coverage_frac * 100:.1f}%)")
        print(f"(RESULTS): Negative coverage (failed):       {failed}/{total} ({negative_frac * 100:.1f}%)")
        print(f"(RESULTS): Please check {self.file_path} for more information regarding the run")
        if len(self.vulnerabilities) > 0:
            print("----------------------DETECTED VULNS-------------------------")
            print(self.get_formatted_vulnerabilites())
        print("---------------------------------------------------------")

    def save(self):
        """Saves the stats into the stats text file
        """
        covered, total, coverage_frac = self.get_coverage_rate()
        failed, _, negative_frac = self.get_negative_coverage_rate()
        with open(self.file_path, "w") as f:
            f.write("\n===================HTTP Status Codes===================\n")
            f.write(json.dumps(self.http_status_codes, indent=4))
            f.write("\n===================Successful Nodes===================\n")
            f.write(json.dumps(self.successful_nodes, indent=4))
            f.write("\n===================Failed Nodes===================\n")
            f.write(json.dumps(self.failed_nodes, indent=4))
            f.write("\n===================General stats ===================\n")
            f.write(f"\nTime taken: {str(time.time() - self.start_time)} seconds")
            # Operation coverage: operations with >=1 success (HTTP 200, no GraphQL 'errors' field)
            f.write(f"\nOperation coverage (successful):  {covered}/{total} ({coverage_frac * 100:.1f}%)")
            # Kept for backward compatibility with test utilities
            f.write(f"\nNumber of unique query/mutation successes: {covered}/{total}")
            # Negative coverage: operations with >=1 failure (any non-success result)
            f.write(f"\nNegative coverage (failed):       {failed}/{total} ({negative_frac * 100:.1f}%)")
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
        self.save_json()

        # Saves the pickle file as well
        self.__save_pickle()

    def save_json(self):
        """Saves a machine-readable JSON report alongside the text stats file"""
        json_path = getattr(self, "json_file_path", None)
        if json_path is None:
            return
        covered, total, coverage_frac = self.get_coverage_rate()
        failed, _, negative_frac = self.get_negative_coverage_rate()
        report = {
            "time_taken_seconds": time.time() - self.start_time,
            "number_of_queries": self.number_of_queries,
            "number_of_mutations": self.number_of_mutations,
            "number_of_objects": self.number_of_objects,
            "number_of_successes": self.number_of_successes,
            "number_of_failures": self.number_of_failures,
            # operation_coverage: unique ops with >=1 HTTP-200/no-errors response / total ops
            "operation_coverage": {"covered": covered, "total": total, "rate": round(coverage_frac, 4)},
            # negative_coverage: unique ops with >=1 failure / total ops
            "negative_coverage": {"failed": failed, "total": total, "rate": round(negative_frac, 4)},
            "http_status_codes": self.http_status_codes,
            "successful_nodes": self.successful_nodes,
            "failed_nodes": self.failed_nodes,
            "vulnerabilities": self.vulnerabilities,
            "node_timings": self.node_timings,
        }
        with open(json_path, "w") as f:
            json.dump(report, f, indent=4)

    def save_eval_summary(self):
        """Saves an ablation/evaluation summary to the ``eval/`` directory.

        Only writes when at least one non-default ablation flag is active
        (``USE_OBJECTS_BUCKET=False``, ``USE_DEPENDENCY_GRAPH=False``, or
        ``MAX_FUZZING_ITERATIONS != 1``).  Each call appends a timestamped
        entry so multiple runs can be compared side-by-side.
        """
        eval_dir = getattr(self, "eval_dir", None)
        if eval_dir is None:
            return

        is_ablation = (
            not config.USE_OBJECTS_BUCKET
            or not config.USE_DEPENDENCY_GRAPH
            or config.MAX_FUZZING_ITERATIONS != 1
        )
        if not is_ablation:
            return

        eval_dir = Path(eval_dir)
        eval_dir.mkdir(parents=True, exist_ok=True)

        covered, total, coverage_frac = self.get_coverage_rate()
        failed, _, negative_frac = self.get_negative_coverage_rate()

        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "ablation_config": {
                "USE_OBJECTS_BUCKET": config.USE_OBJECTS_BUCKET,
                "USE_DEPENDENCY_GRAPH": config.USE_DEPENDENCY_GRAPH,
                "MAX_FUZZING_ITERATIONS": config.MAX_FUZZING_ITERATIONS,
                "DISABLE_MUTATIONS": config.DISABLE_MUTATIONS,
                "ALLOW_DELETION_OF_OBJECTS": config.ALLOW_DELETION_OF_OBJECTS,
            },
            "results": {
                "time_taken_seconds": round(time.time() - self.start_time, 2),
                "number_of_queries": self.number_of_queries,
                "number_of_mutations": self.number_of_mutations,
                "number_of_objects": self.number_of_objects,
                "number_of_successes": self.number_of_successes,
                "number_of_failures": self.number_of_failures,
                "operation_coverage": {"covered": covered, "total": total, "rate": round(coverage_frac, 4)},
                "negative_coverage": {"failed": failed, "total": total, "rate": round(negative_frac, 4)},
                "vulnerabilities_found": {
                    vuln: {node: info.get("is_vulnerable", False) for node, info in nodes.items()}
                    for vuln, nodes in self.vulnerabilities.items()
                },
            },
        }

        # Append to a cumulative JSONL file so multiple runs stack up
        runs_file = eval_dir / "ablation_runs.jsonl"
        with open(runs_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Also write a human-readable summary
        summary_file = eval_dir / "ablation_summary.txt"
        with open(summary_file, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Run at: {entry['timestamp']}\n")
            f.write(f"  USE_OBJECTS_BUCKET    : {config.USE_OBJECTS_BUCKET}\n")
            f.write(f"  USE_DEPENDENCY_GRAPH  : {config.USE_DEPENDENCY_GRAPH}\n")
            f.write(f"  MAX_FUZZING_ITERATIONS: {config.MAX_FUZZING_ITERATIONS}\n")
            f.write(f"  DISABLE_MUTATIONS     : {config.DISABLE_MUTATIONS}\n")
            f.write(f"  ALLOW_DELETION        : {config.ALLOW_DELETION_OF_OBJECTS}\n")
            f.write("Results:\n")
            f.write(f"  Time taken    : {entry['results']['time_taken_seconds']}s\n")
            f.write(f"  Coverage      : {covered}/{total} ({coverage_frac * 100:.1f}%)\n")
            f.write(f"  Neg. coverage : {failed}/{total} ({negative_frac * 100:.1f}%)\n")
            f.write(f"  Successes     : {self.number_of_successes}\n")
            f.write(f"  Failures      : {self.number_of_failures}\n")
            if self.vulnerabilities:
                f.write(f"  Vulnerabilities: {list(self.vulnerabilities.keys())}\n")

    def save_endpoint_results(self):
        """Reads the results, for each node in the node name -> results, create a directory for the
           result type, then a file for the response code, and append the payload and the response to the file.
        """
        unique_results = {}
        # Filter out for only unique results
        for node_name, results in self.results.items():
            # If the node name has slashes, replace them with underscores
            node_name = node_name.replace("/", "_")

            if os.name == "nt":
                # Replace characters that are invalid in Windows filenames
                node_name = re.sub(r'[\\/:*?"<>|]', "_", node_name)

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
            try:
                with open(self.pickle_save_path, "rb") as file:
                    loaded_stats = pickle.load(file)
                    self.__dict__.update(loaded_stats.__dict__)
            except (EOFError, Exception):
                # File may be empty or corrupt (e.g. child process killed mid-write); skip load.
                pass
