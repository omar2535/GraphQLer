"""Class for fuzzer

1. Gets all nodes that can be run without a dependency (query/mutation)
2. Adds these to the DFS queue
3. 1st Pass: Perform DFS, going through only creation nodes
4. 2nd Pass: Perform DFS, allow also queries and updates
5. 3rd Pass: Perform DFS, allow deletions
6. Clean up
"""

import multiprocessing
import random
import threading
import time

import networkx
import typing

from graphqler import config
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

        # Stats about the run
        self.dfs_ran_nodes: set[Node] = set()
        self.stats.number_of_queries = self.api.get_num_queries()
        self.stats.number_of_mutations = self.api.get_num_mutations()
        self.stats.number_of_objects = self.api.get_num_objects()

    def run(self):
        """Main function to run the fuzzer"""
        # Create a separate thread / process so that we can kill it if it takes too long / times out
        queue = multiprocessing.Queue()
        if config.DEBUG:
            p = threading.Thread(target=self.__run_steps, args=(queue,))
            p.daemon = True
        else:
            p = multiprocessing.Process(target=self.__run_steps, args=(queue,))
        p.start()
        p.join(config.MAX_TIME)

        # Terminate the process if it's still alive after the max time
        if p.is_alive() and isinstance(p, multiprocessing.Process):
            print(f"(+) Terminating the fuzzer process - reached max time {config.MAX_TIME}s")
            p.terminate()

        # Get results from the process
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
        """Runs the fuzzer. Performs steps as follows:
        1. Gets all nodes that can be run without a dependency (query/mutation)
        2. 1st Pass: Perform DFS, going through only CREATE nodes and query nodes
        3. 2nd Pass: Perform DFS, allow UPDATE as well as CREATE and also query nodes
        4. 3rd Pass: Perform DFS, allow DELETE and UNKNOWN
        5. Get all nodes that still haven't been ran, run them (these are the nodes that may be in islands of the graph - very rare)
        6. Run detections on the API
        7. Finish

        Args:
            queue (multiprocessing.Queue): The queue to send the objects bucket to
        """
        # Step 1
        starter_nodes: list[Node] = self._get_starter_nodes()
        self.logger.info(f"Starter nodes: {starter_nodes}")
        self.stats.start_time = time.time()

        # Step 2
        self.__perform_dfs(starter_stack=starter_nodes, filter_mutation_type=["UPDATE", "DELETE", "UNKNOWN"])
        self.logger.info("Completed 1st pass using CREATE and QUERY")
        self.logger.info(f"Objects bucket: {self.objects_bucket}")

        # Step 3
        self.__perform_dfs(starter_stack=starter_nodes, filter_mutation_type=["DELETE", "UNKNOWN"])
        self.logger.info("Completed 2nd pass using CREATE, QUERY, UPDATE")
        self.logger.info(f"Objects bucket: {self.objects_bucket}")

        # Step 4
        self.__perform_dfs(starter_stack=starter_nodes, filter_mutation_type=[])
        self.logger.info("Completed 3rd pass using all available mutations and queries")
        self.logger.info(f"Objects bucket: {self.objects_bucket}")

        # Step 5
        nodes_to_run = [node for node in self.dependency_graph.nodes if node not in self.dfs_ran_nodes]
        self.__run_nodes(nodes_to_run)
        self.logger.info("Completed running all nodes that haven't been ran yet")

        # Step 6
        self.dengine.run_detections_on_api()
        self.logger.info("Completed running detections on the overall API")

        # Step 7: Finish
        self.logger.info("Completed fuzzing")
        self.logger.info(f"Objects bucket: {self.objects_bucket}")
        self.stats.print_results()
        self.stats.save()
        self.objects_bucket.save()

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
            _next_visit_path, result = self.__run_node(current_node, [current_node], check_hard_depends_on=False)

            # Upddate the stats
            self.stats.update_stats_from_result(current_node, result)

            # If it was a success, then update the objects bucket
            if result.success:
                self.logger.info(f"Node was successful: {current_node}")

    def __perform_dfs(self, starter_stack: list[Node], filter_mutation_type: list[str]):
        """Performs DFS with the initial starter stack

        Args:
            starter_stack (list[Node]): A list of the nodes to start the fuzzing
            filter_mutation_type (list[str]): A list of mutation types to filter out when performing DFS (IE. [UPDATE,UNKNOWN,DELETE])
        """

        # DFS visit specific
        visited: list[Node] = []
        failed_visited: dict = {}
        to_visit: list[list[Node]] = [[n] for n in starter_stack]

        # Initialize some counters for cases when we need to break out of DFS
        max_run_times = (len(self.dependency_graph.nodes) + len(self.dependency_graph.edges)) * 10
        run_times = 0
        max_requeue_for_same_node = 3

        while len(to_visit) != 0:
            self.stats.print_running_stats()

            # Now for the actual DFS
            current_visit_path: list[Node] = to_visit.pop()
            current_node: Node = current_visit_path[-1]
            self.logger.info(f"Current node: {current_node}")

            if current_node not in visited and current_node.mutation_type not in filter_mutation_type:  # skip over any nodes that are in the filter_mutation_type
                new_paths_to_evaluate, res = self.__run_node(current_node, current_visit_path)
                self.stats.update_stats_from_result(current_node, res)  # Update the stats

                # If it's not successful:
                # then we check if it's exceeded the max retries
                # If it is, then we dont re-queue the node
                if not res.success:
                    self.logger.info(f"[{current_node}]Node was not successful")
                    if current_node.name in failed_visited and failed_visited[current_node.name] >= max_requeue_for_same_node:
                        continue  # Stop counting failures, already max retries reached
                    else:
                        failed_visited[current_node.name] = failed_visited[current_node.name] + 1 if current_node.name in failed_visited else 1
                        to_visit.insert(0, current_visit_path)  # Will retry later, put it at the back of the stack
                else:
                    self.logger.info(f"[{current_node}]Node was successful")
                    to_visit.extend(new_paths_to_evaluate)  # Will keep going deeper, put new paths at the front of the stack
                    visited.append(current_node)  # We've visited this node, so add it to the visited list

                    if current_node.name in failed_visited:  # If it was in the failed visited, remove it since it passed
                        del failed_visited[current_node.name]

                # Mark the node as dfs used (independent from visited since visited is used for each run, dfs_ran_nodes is noted for all 3 DFS phases)
                self.dfs_ran_nodes.add(current_node)
                self.logger.debug(f"Visited: {visited}")
                self.logger.debug(f"Failed visited: {failed_visited}")
                self.logger.debug(f"Objects bucket: {self.objects_bucket}")

            # Break out condition from the loop
            # - Max run times reached
            run_times += 1
            if run_times >= max_run_times:
                self.logger.info("Hit max run times. Ending DFS")
                break

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
        new_paths_to_evaluate, res = self.__evaluate(node, visit_path, check_hard_depends_on=check_hard_depends_on)  # For positive testing (normal run)
        self.__fuzz(node, visit_path)  # For negative testing (fuzzing)
        self.__detect_vulnerabilities_on_node(node)  # For negative testing (Detect vulnerabilities)
        return (new_paths_to_evaluate, res)

    def __evaluate(self, node: Node, visit_path: list[Node], check_hard_depends_on: bool = True) -> tuple[list[list[Node]], Result]:
        """Evaluates the path, performing the following based on the type of node:
           Case 1: If it's an object node, then we should check if the object is in our bucket. If not, fail, if it is,
                   then queue up the next neighboring nodes to visit
           Case 2: If it's an query node or mutation node, run the payload with the required objects, then store the results in the object bucket

        Args:
            node (Node): Node to be evaluated
            visit_path (list[Node]): The list of visited paths to arrive at the node
            check_hard_depends_n (bool): The check hard depends on flag for materializing the object

        Returns:
            tuple[list[list[Node]], Result]: A list of the next to_visit paths, and the result of the node evaluation
        """
        neighboring_nodes = self._get_neighboring_nodes(node)
        new_visit_paths = self._get_new_visit_path_with_neighbors(neighboring_nodes, visit_path)

        if node.graphql_type == "Object" and check_hard_depends_on:
            if self.objects_bucket.is_object_in_bucket(node.name):
                return (new_visit_paths, Result(ResultEnum.GENERAL_SUCCESS))
            else:
                return ([], Result(ResultEnum.INTERNAL_FAILURE))
        else:
            _graphql_response, res = self.fengine.run_minimal_payload(node.name, self.objects_bucket, node.graphql_type, check_hard_depends_on=check_hard_depends_on)
            if res.success:
                return (new_visit_paths, res)
            else:
                return ([], res)

    def __fuzz(self, node: Node, visit_path: list[Node]):
        """Fuzzes a node by running the node and storing the results. Currently runs:
           - DOS Query / Mutation (from size 0 to MAX_INPUT_DEPTH or HARD_CUTOFF_DEPTH, whichever is smaller)

        Args:
            node (Node): The node to fuzz
            visit_path (list[Node]): The list of visited paths to arrive at the node
        """
        # If not a query or mutation, just return since there's nothing to fuzz / send to the host
        if node.graphql_type not in ["Query", "Mutation"]:
            return
        # DOS Query / Mutation
        if not config.SKIP_DOS_ATTACKS and config.MAX_FUZZING_ITERATIONS != 0:
            random_numbers = [random.randint(1, min(config.HARD_CUTOFF_DEPTH, config.MAX_INPUT_DEPTH)) for _ in range(0, config.MAX_FUZZING_ITERATIONS)]
            random_number = random.choice(random_numbers)
            self.logger.info(f"Running DOS {node.graphql_type}: {node.name} with depth: {random_number}")
            results = self.fengine.run_dos_payloads(node.name, self.objects_bucket, node.graphql_type, random_number)
            for _graphql_response, res in results:
                self.stats.update_stats_from_result(node, res)

        # Run the maximal payloads as part of the fuzz (always runs because this is just the maximal output in queries / mutations)
        if not config.SKIP_MAXIMAL_PAYLOADS:
            self.fengine.run_maximal_payload(node.name, self.objects_bucket, node.graphql_type, check_hard_depends_on=False)

    def __detect_vulnerabilities_on_node(self, node: Node):
        if node.graphql_type in ["Query", "Mutation"]:
            self.dengine.run_detections_on_graphql_object(node, self.objects_bucket, node.graphql_type)

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
           First, looks for independent nodes. If no independent nodes are found,
           then nodes with the fewest dependencies are returned, if there aren't any, then returns random nodes

        Returns:
            list[Node]: A list of starter nodes
        """
        in_degree_centrality = networkx.in_degree_centrality(self.dependency_graph)
        for num_dependencies in range(0, 100000):  # choose a very large number, most likely never hit it
            nodes = [node for node, centrality in in_degree_centrality.items() if centrality == num_dependencies]
            if len(nodes) != 0:
                return nodes

        # This shouldn't ever be hit, but in case, then we choose random nodes as the starter nodes
        self.logger.error("No starter nodes found, choosing a random node")
        return [random.choice(list(self.dependency_graph.nodes))]
