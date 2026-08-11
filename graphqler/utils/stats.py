import json
import os
import pprint
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Self

from graphqler import config
from graphqler.fuzzer.engine.types import Result, ResultEnum
from graphqler.graph import Node

from .file_utils import atomic_write_json, initialize_file, read_json_file, recreate_path


class Stats:
    ### PUT THE STATS YOU WANT HERE
    file_path = "/tmp/stats.txt"  # This gets overriden by the set_file_path function
    endpoint_results_dir = "/tmp/endpoint_results"
    unique_responses_file_path = "/tmp/unique_responses.txt"
    start_time: float = 0.0
    http_status_codes: dict[str, dict[str, int]] = {}
    successful_nodes: dict[str, int] = {}
    failed_nodes: dict[str, int] = {}
    results: dict[str, set[Result]] = {}  # Mapping of query/mutation to results for that node
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

    # Phase tracking ("chains" | "islands" | "dep_retry" | "detections")
    phase: str = "chains"
    islands_total: int = 0
    islands_completed: int = 0
    dep_retry_total: int = 0
    dep_retry_completed: int = 0
    dep_retry_nodes: list[str] = []

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
        self.dep_retry_total = 0
        self.dep_retry_completed = 0
        self.dep_retry_nodes = []
        self.state_save_path = Path(config.OUTPUT_DIRECTORY) / config.SERIALIZED_DIR_NAME / config.STATS_STATE_FILE_NAME
        self._last_checkpoint = time.monotonic()

    def load(self) -> Self:
        """Load a versioned JSON stats snapshot."""
        if not self.state_save_path.exists():
            return self
        try:
            state = read_json_file(self.state_save_path)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Unable to read stats state: {self.state_save_path}") from exc
        if state.get("format") != "graphqler.stats" or state.get("version") != 1:
            raise ValueError(f"Unsupported stats state format: {self.state_save_path}")

        for name in (
            "start_time",
            "http_status_codes",
            "successful_nodes",
            "failed_nodes",
            "unique_responses",
            "number_of_queries",
            "number_of_mutations",
            "number_of_objects",
            "number_of_successes",
            "number_of_failures",
            "vulnerabilities",
            "node_timings",
            "is_introspection_available",
            "chains_total",
            "chains_completed",
            "current_iteration",
            "total_iterations",
            "phase",
            "islands_total",
            "islands_completed",
            "dep_retry_total",
            "dep_retry_completed",
            "dep_retry_nodes",
        ):
            if name in state:
                setattr(self, name, state[name])
        self.results = {name: {Result.from_dict(result) for result in results} for name, results in state.get("results", {}).items()}
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

    def set_file_paths(self, working_dir: str, reset: bool = True) -> None:
        """Configure report/state paths, optionally preserving an interrupted run."""
        root = Path(working_dir)
        root.mkdir(parents=True, exist_ok=True)
        self.file_path = root / config.STATS_FILE_NAME
        json_file_name = config.STATS_FILE_NAME.replace(".txt", ".json") if config.STATS_FILE_NAME.endswith(".txt") else config.STATS_FILE_NAME + ".json"
        self.json_file_path = root / json_file_name
        self.eval_dir = root / config.EVAL_DIR_NAME
        self.endpoint_results_dir = root / config.ENDPOINT_RESULTS_DIR_NAME
        self.unique_responses_file_path = root / config.UNIQUE_RESPONSES_FILE_NAME
        self.state_save_path = root / config.SERIALIZED_DIR_NAME / config.STATS_STATE_FILE_NAME

        if reset:
            initialize_file(self.file_path)
            initialize_file(self.json_file_path)
            initialize_file(self.unique_responses_file_path)
            if config.SAVE_ENDPOINT_RESULTS:
                recreate_path(self.endpoint_results_dir)
        elif config.SAVE_ENDPOINT_RESULTS:
            self.endpoint_results_dir.mkdir(parents=True, exist_ok=True)

    def print_running_stats(self):
        """Print a single-line progress update that overwrites itself each second."""
        elapsed = time.time() - self.start_time
        elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
        counts = f"✓ {self.number_of_successes} | ✗ {self.number_of_failures}"

        if self.phase == "detections":
            progress = f"[Detections] {counts} | {elapsed_str} elapsed"
        elif self.phase == "dep_retry":
            progress = f"[Dep-Retry {self.dep_retry_completed}/{self.dep_retry_total}] {counts} | {elapsed_str} elapsed"
        elif self.phase == "islands":
            progress = f"[Islands {self.islands_completed}/{self.islands_total}] {counts} | {elapsed_str} elapsed"
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
                f"[Iter {self.current_iteration}/{self.total_iterations} | Chain {self.chains_completed}/{self.chains_total}] {counts} | {elapsed_str} elapsed | ETA {eta_str}"
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
        # Hard dependency not met means the node was never executed — skip all tracking
        if result.result_enum == ResultEnum.HARD_DEPENDENCY_NOT_MET:
            return

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
        self.maybe_checkpoint()

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
        """Saves the stats into the stats text file"""
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
        if config.SAVE_ENDPOINT_RESULTS:
            self.save_endpoint_results()
        self.save_unique_response()
        self.save_json()
        self.checkpoint()

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
        atomic_write_json(report, json_path)

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

        is_ablation = not config.USE_OBJECTS_BUCKET or not config.USE_DEPENDENCY_GRAPH or config.MAX_FUZZING_ITERATIONS != 1
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
                "vulnerabilities_found": {vuln: {node: info.get("is_vulnerable", False) for node, info in nodes.items()} for vuln, nodes in self.vulnerabilities.items()},
            },
        }

        # Append to a cumulative JSONL file so multiple runs stack up
        runs_file = eval_dir / "ablation_runs.jsonl"
        with open(runs_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Also write a human-readable summary
        summary_file = eval_dir / "ablation_summary.txt"
        with open(summary_file, "a") as f:
            f.write(f"\n{'=' * 60}\n")
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
        """Rewrite deterministic, de-duplicated result files for each endpoint."""
        recreate_path(Path(self.endpoint_results_dir))
        unique_results: dict[Path, dict[str, object]] = {}
        for raw_node_name, results in self.results.items():
            node_name = raw_node_name.replace("/", "_")
            if os.name == "nt":
                node_name = re.sub(r'[\\/:*?"<>|]', "_", node_name)

            for result in results:
                result_type = "success" if result.success else "failure"
                result_file_path = Path(self.endpoint_results_dir) / node_name / result_type / str(result.status_code)
                unique_results.setdefault(result_file_path, {})[str(result.payload)] = result.graphql_response

        for result_file_path, payloads in sorted(unique_results.items(), key=lambda item: str(item[0])):
            result_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(result_file_path, "w") as file_handle:
                for payload, response in sorted(payloads.items()):
                    file_handle.write("------------------Payload:-------------------\n")
                    file_handle.write(f"{payload}\n")
                    file_handle.write("------------------Response:-------------------\n")
                    file_handle.write(f"{response}\n")

    def save_unique_response(self):
        """Save unique responses and the operations that returned them."""
        with open(Path(self.unique_responses_file_path), "w") as file_handle:
            for response, endpoints in self.unique_responses.items():
                file_handle.write(f"Response: {response}\n")
                file_handle.write(f"Endpoints: {endpoints}\n")

    def _state(self) -> dict:
        return {
            "format": "graphqler.stats",
            "version": 1,
            "start_time": self.start_time,
            "http_status_codes": self.http_status_codes,
            "successful_nodes": self.successful_nodes,
            "failed_nodes": self.failed_nodes,
            "results": {name: [result.to_dict() for result in results] for name, results in self.results.items()},
            "unique_responses": self.unique_responses,
            "number_of_queries": self.number_of_queries,
            "number_of_mutations": self.number_of_mutations,
            "number_of_objects": self.number_of_objects,
            "number_of_successes": self.number_of_successes,
            "number_of_failures": self.number_of_failures,
            "vulnerabilities": self.vulnerabilities,
            "node_timings": self.node_timings,
            "is_introspection_available": self.is_introspection_available,
            "chains_total": self.chains_total,
            "chains_completed": self.chains_completed,
            "current_iteration": self.current_iteration,
            "total_iterations": self.total_iterations,
            "phase": self.phase,
            "islands_total": self.islands_total,
            "islands_completed": self.islands_completed,
            "dep_retry_total": self.dep_retry_total,
            "dep_retry_completed": self.dep_retry_completed,
            "dep_retry_nodes": self.dep_retry_nodes,
        }

    def checkpoint(self) -> None:
        """Atomically persist a compact run snapshot."""
        atomic_write_json(self._state(), self.state_save_path)
        self._last_checkpoint = time.monotonic()

    def maybe_checkpoint(self, interval_seconds: float = 5.0) -> None:
        """Persist at most once per interval while a run is active."""
        if time.monotonic() - self._last_checkpoint >= interval_seconds:
            self.checkpoint()
