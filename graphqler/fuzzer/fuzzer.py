"""Class for fuzzer

1. Loads pre-generated chains from the compilation step
2. Pass 1: Run chains that contain only CREATE/QUERY nodes
3. Pass 2: Run chains that also allow UPDATE nodes
4. Pass 3: Run all chains (including DELETE/UNKNOWN)
5. Clean up
"""

import multiprocessing
import random
import threading
import time

import typing

from graphqler import config
from graphqler.chains import Chain, ChainGenerator
from graphqler.graph import GraphGenerator, Node
from graphqler.utils.api import API
from graphqler.utils.logging_utils import Logger
from graphqler.utils.objects_bucket import ObjectsBucket
from graphqler.utils.stats import Stats

from .engine.fengine import FEngine
from .engine.dengine import DEngine
from .engine.types import Result, ResultEnum


class Fuzzer(object):
    def __init__(self, save_path: str, url: str, objects_bucket: typing.Optional[ObjectsBucket] = None):
        """Initializes the fuzzer, reading information from the compiled files

        Args:
            save_path (str): Save directory path
            url (str): URL for graphql introspection query to hit
        """
        self.save_path = save_path
        self.url = url
        self.logger = Logger().get_fuzzer_logger()
        self.stats = Stats()
        self.api = API(url, save_path)

        self.dependency_graph = GraphGenerator(save_path).get_dependency_graph()
        self.fengine = FEngine(self.api)
        self.dengine = DEngine(self.api)

        if objects_bucket:
            self.objects_bucket = objects_bucket
        else:
            self.objects_bucket = ObjectsBucket(self.api)

        # Load pre-generated chains produced during compilation
        self.chains: list[Chain] = ChainGenerator().load_from_yaml(save_path, self.dependency_graph)

        # Stats about the run
        self.stats.number_of_queries = self.api.get_num_queries()
        self.stats.number_of_mutations = self.api.get_num_mutations()
        self.stats.number_of_objects = self.api.get_num_objects()

    def run(self):
        """Main function to run the fuzzer"""
        queue = multiprocessing.Queue()
        if config.DEBUG:
            p = threading.Thread(target=self.__run_steps, args=(queue,))
            p.daemon = True
        else:
            p = multiprocessing.Process(target=self.__run_steps, args=(queue,))
        p.start()
        p.join(config.MAX_TIME)

        if p.is_alive() and isinstance(p, multiprocessing.Process):
            print(f"(+) Terminating the fuzzer process - reached max time {config.MAX_TIME}s")
            p.terminate()

        if not queue.empty():
            _ = queue.get()

    def run_single(self, node_name: str):
        """Runs a single node

        Args:
            node_name (str): The name of the node
        """
        node = [n for n in self.dependency_graph.nodes if n.name == node_name]
        if len(node) == 0:
            print(f"(F) Node `{node_name}` not found")
            self.logger.error(f"Node `{node_name}` not found")
            return

        self.stats.start_time = time.time()
        self.__run_nodes(node)
        self.logger.info("Completed fuzzing")
        self.stats.print_results()
        self.stats.save()
        self.objects_bucket.save()

    def run_no_dfs(self):
        """Runs the fuzzer without using the dependency graph. Just uses each node and tests against the server

        Returns:
            dict: The objects bucket
        """
        nodes_to_run = list(self.dependency_graph.nodes)
        self.__run_nodes(nodes_to_run)
        self.logger.info("Completed fuzzing")
        self.stats.print_results()
        self.stats.save()
        self.objects_bucket.save()

    def __run_steps(self, queue: multiprocessing.Queue):
        """Runs the fuzzer using pre-generated chains. Steps:
        1. Execute each chain in order (pass/filter ordering handled by the compiler)
        2. Run any nodes not covered by the chains (island nodes)
        3. Run detections on the overall API
        4. Finish

        Args:
            queue (multiprocessing.Queue): Queue for communicating back to the parent process
        """
        self.stats.start_time = time.time()

        if self.chains:
            self.logger.info(f"Running {len(self.chains)} pre-generated chains")
            for chain in self.chains:
                self.__run_chain(chain)
            self.logger.info("Completed all chains")

            # Run any nodes not covered by any chain (e.g. isolated nodes)
            chained_nodes: set[Node] = {node for chain in self.chains for node in chain.nodes}
            uncovered_nodes = [node for node in self.dependency_graph.nodes if node not in chained_nodes]
        else:
            # Fallback: no chains available (compiler not run or old compilation), execute all nodes
            self.logger.warning("No chains found — falling back to running all nodes directly")
            uncovered_nodes = list(self.dependency_graph.nodes)

        if uncovered_nodes:
            self.logger.info(f"Running {len(uncovered_nodes)} uncovered node(s)")
            self.__run_nodes(uncovered_nodes)

        # Detections
        self.dengine.run_detections_on_api()
        self.logger.info("Completed running detections on the overall API")

        # Finish
        self.logger.info("Completed fuzzing")
        self.logger.info(f"Objects bucket: {self.objects_bucket}")
        self.stats.print_results()
        self.stats.save()
        self.objects_bucket.save()

    def __run_chain(self, chain: Chain):
        """Executes every node in the chain sequentially using a **fresh** ObjectsBucket.

        A new non-singleton ObjectsBucket is created for each chain so that objects
        accumulated during this chain's execution do not leak into other chains.
        The global Stats singleton is updated throughout.

        Args:
            chain (Chain): The chain to execute.
        """
        # Create a fresh, non-singleton ObjectsBucket for this chain
        fresh_bucket: ObjectsBucket = ObjectsBucket.__wrapped__(self.api)

        self.logger.info(f"Running chain: {chain}")
        for node in chain.nodes:
            if node.name in config.SKIP_NODES:
                continue
            self.stats.print_running_stats()
            self.logger.info(f"[chain] Running node: {node}")
            node_start = time.time()
            _next_paths, result = self.__evaluate(node, list(chain.nodes[:chain.nodes.index(node) + 1]),
                                                  objects_bucket=fresh_bucket)
            self.stats.record_node_timing(node, time.time() - node_start)
            self.stats.update_stats_from_result(node, result)

            self.__fuzz(node, list(chain.nodes[:chain.nodes.index(node) + 1]), objects_bucket=fresh_bucket)
            self.__detect_vulnerabilities_on_node(node, fresh_bucket)

            if not result.success:
                # If a prerequisite node fails, the rest of the chain cannot proceed
                self.logger.info(f"[chain] Node {node} failed — stopping chain execution early")
                break

    def __run_nodes(self, nodes: list[Node]):
        """Runs the nodes given in the list

        Args:
            nodes (list[Node]): List of nodes to run

        Raises:
            Exception: If the GraphQL type of the node is unknown
        """
        for current_node in nodes:
            self.stats.print_running_stats()
            self.logger.info(f"Running node: {current_node}")
            node_start = time.time()
            _next_visit_path, result = self.__run_node(current_node, [current_node], check_hard_depends_on=False)
            self.stats.record_node_timing(current_node, time.time() - node_start)
            self.stats.update_stats_from_result(current_node, result)

            if result.success:
                self.logger.info(f"Node was successful: {current_node}")

    def __run_node(self, node: Node, visit_path: list[Node], check_hard_depends_on: bool = True) -> tuple[list[list[Node]], Result]:
        """Runs the node, evaluating it and return the next visit paths.
           - The return will be based on the positive testing of the node
           - The side effects will be the fuzzed node and the detection of any vulnerabilities on the node

        Args:
            node (Node): The node
            visit_path (list[Node]): The visit path
            check_hard_depends_on (bool, optional): Whether to check the dependencies. Defaults to True.

        Returns:
            tuple[list[list[Node]], Result]: The results of the positive node evaluation
        """
        if node.name in config.SKIP_NODES:
            return ([], Result(ResultEnum.GENERAL_SUCCESS))
        new_paths_to_evaluate, res = self.__evaluate(node, visit_path, check_hard_depends_on=check_hard_depends_on)
        self.__fuzz(node, visit_path)
        self.__detect_vulnerabilities_on_node(node)
        return (new_paths_to_evaluate, res)

    def __evaluate(self, node: Node, visit_path: list[Node], check_hard_depends_on: bool = True,
                   objects_bucket: typing.Optional[ObjectsBucket] = None) -> tuple[list[list[Node]], Result]:
        """Evaluates the path, performing the following based on the type of node:
           Case 1: If it's an object node, then we should check if the object is in our bucket. If not, fail, if it is,
                   then queue up the next neighboring nodes to visit
           Case 2: If it's an query node or mutation node, run the payload with the required objects, then store the results in the object bucket

        Args:
            node (Node): Node to be evaluated
            visit_path (list[Node]): The list of visited paths to arrive at the node
            check_hard_depends_on (bool): The check hard depends on flag for materializing the object
            objects_bucket (ObjectsBucket | None): Bucket to use; defaults to self.objects_bucket

        Returns:
            tuple[list[list[Node]], Result]: A list of the next to_visit paths, and the result of the node evaluation
        """
        bucket = objects_bucket if objects_bucket is not None else self.objects_bucket
        neighboring_nodes = self._get_neighboring_nodes(node)
        new_visit_paths = self._get_new_visit_path_with_neighbors(neighboring_nodes, visit_path)

        if node.graphql_type == "Object" and check_hard_depends_on:
            if bucket.is_object_in_bucket(node.name):
                return (new_visit_paths, Result(ResultEnum.GENERAL_SUCCESS))
            else:
                return ([], Result(ResultEnum.INTERNAL_FAILURE))
        else:
            _graphql_response, res = self.fengine.run_minimal_payload(node.name, bucket, node.graphql_type, check_hard_depends_on=check_hard_depends_on)
            if res.success:
                return (new_visit_paths, res)
            else:
                return ([], res)

    def __fuzz(self, node: Node, visit_path: list[Node], objects_bucket: typing.Optional[ObjectsBucket] = None):
        """Fuzzes a node by running the node and storing the results. Currently runs:
           - DOS Query / Mutation (from size 0 to MAX_INPUT_DEPTH or HARD_CUTOFF_DEPTH, whichever is smaller)

        Args:
            node (Node): The node to fuzz
            visit_path (list[Node]): The list of visited paths to arrive at the node
            objects_bucket (ObjectsBucket | None): Bucket to use; defaults to self.objects_bucket
        """
        bucket = objects_bucket if objects_bucket is not None else self.objects_bucket
        if node.graphql_type not in ["Query", "Mutation"]:
            return
        if not config.SKIP_DOS_ATTACKS and config.MAX_FUZZING_ITERATIONS != 0:
            random_numbers = [random.randint(1, min(config.HARD_CUTOFF_DEPTH, config.MAX_INPUT_DEPTH)) for _ in range(0, config.MAX_FUZZING_ITERATIONS)]
            random_number = random.choice(random_numbers)
            self.logger.info(f"Running DOS {node.graphql_type}: {node.name} with depth: {random_number}")
            results = self.fengine.run_dos_payloads(node.name, bucket, node.graphql_type, random_number)
            for _graphql_response, res in results:
                self.stats.update_stats_from_result(node, res)

        if not config.SKIP_MAXIMAL_PAYLOADS:
            self.fengine.run_maximal_payload(node.name, bucket, node.graphql_type, check_hard_depends_on=False)

    def __detect_vulnerabilities_on_node(self, node: Node, objects_bucket: typing.Optional[ObjectsBucket] = None):
        bucket = objects_bucket if objects_bucket is not None else self.objects_bucket
        if node.graphql_type in ["Query", "Mutation"]:
            self.dengine.run_detections_on_graphql_object(node, bucket, node.graphql_type)

    # ------------------- Helpers -------------------

    def _get_new_visit_path_with_neighbors(self, neighboring_nodes: list[Node], visit_path: list[Node]) -> list[list[Node]]:
        """Gets the new visit path with the neighbors by creating a new path for each neighboring node

        Args:
            neighboring_nodes (list[Node]): The list of neighboring nodes
            visit_path (list[Node]): The visit path that the current iteration is on

        Returns:
            list[list[Node]]: A list of visit_paths where each visit_path is just the visit_path + neighboring_node
        """
        new_visit_paths = []
        for node in neighboring_nodes:
            new_visit_paths.append(visit_path + [node])
        return new_visit_paths

    def _get_neighboring_nodes(self, node: Node) -> list[Node]:
        """Get nodes that this node goes out of

        Args:
            node (Node): The node we want to find that is pointing to this node

        Returns:
            list[Node]: List of nodes that are dependent on the input node
        """
        return [n for n in self.dependency_graph.successors(node)]

    def _get_starter_nodes(self) -> list[Node]:
        """Gets a list of starter nodes to start the fuzzing with.
           First, looks for nodes with no incoming edges (in-degree == 0).
           If none exist, returns nodes with the minimum in-degree.

        Returns:
            list[Node]: A list of starter nodes
        """
        in_degrees = dict(self.dependency_graph.in_degree())
        if not in_degrees:
            self.logger.error("No nodes in dependency graph")
            return []

        min_degree = min(in_degrees.values())
        nodes = [node for node, degree in in_degrees.items() if degree == min_degree]
        if nodes:
            return nodes

        self.logger.error("No starter nodes found, choosing a random node")
        return [random.choice(list(self.dependency_graph.nodes))]
