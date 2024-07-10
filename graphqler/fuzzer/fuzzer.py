"""Class for fuzzer

1. Gets all nodes that can be run without a dependency (query/mutation)
2. Adds these to the DFS queue
3. 1st Pass: Perform DFS, going through only creation nodes
4. 2nd Pass: Perform DFS, allow also queries and updates
5. 3rd Pass: Perform DFS, allow deletions
6. Clean up
"""

from pathlib import Path
from graphqler.graph import GraphGenerator, Node
from graphqler.utils.file_utils import read_yaml_to_dict
from graphqler.utils.logging_utils import Logger
from graphqler.utils.stats import Stats
from .fengine.fengine import FEngine
from .fengine.types import Result

import multiprocessing
from graphqler import constants
import networkx
import random
import time


class Fuzzer(object):
    def __init__(self, save_path: str, url: str):
        """Initializes the fuzzer, reading information from the compiled files

        Args:
            save_path (str): Save directory path
            url (str): URL for graphql introspection query to hit
        """
        self.save_path = save_path
        self.url = url
        self.logger = Logger().get_fuzzer_logger()
        self.stats = Stats()

        self.compiled_queries_save_path = Path(save_path) / constants.COMPILED_QUERIES_FILE_NAME
        self.compiled_objects_save_path = Path(save_path) / constants.COMPILED_OBJECTS_FILE_NAME
        self.compiled_mutations_save_path = Path(save_path) / constants.COMPILED_MUTATIONS_FILE_NAME
        self.extracted_enums_save_path = Path(save_path) / constants.ENUM_LIST_FILE_NAME
        self.extracted_input_objects_save_path = Path(save_path) / constants.INPUT_OBJECT_LIST_FILE_NAME

        self.queries = read_yaml_to_dict(self.compiled_queries_save_path)
        self.objects = read_yaml_to_dict(self.compiled_objects_save_path)
        self.mutations = read_yaml_to_dict(self.compiled_mutations_save_path)
        self.input_objects = read_yaml_to_dict(self.extracted_input_objects_save_path)
        self.enums = read_yaml_to_dict(self.extracted_enums_save_path)

        self.dependency_graph = GraphGenerator(save_path).get_dependency_graph()
        self.fengine = FEngine(self.queries, self.objects, self.mutations, self.input_objects, self.enums, self.url, self.save_path)

        self.objects_bucket = {}

        # Stats about the run
        self.dfs_ran_nodes: set[Node] = set()
        self.stats.number_of_queries = len(self.queries.keys())
        self.stats.number_of_mutations = len(self.mutations.keys())
        self.stats.number_of_objects = len(self.objects.keys())

    def run(self) -> dict:
        """Runs the fuzzer

        Returns:
            dict: The objects bucket
        """
        # Create a separate process
        queue = multiprocessing.Queue()
        p = multiprocessing.Process(target=self.__run_steps, args=(queue,))
        p.start()
        p.join(constants.MAX_TIME)

        # Terminate the thread if it's still alive after the max time
        if p.is_alive():
            print(f"(+) Terminating the fuzzer process - reached max time {constants.MAX_TIME}s")
            p.terminate()
        p.join()

        # Get results from objects bucket
        if not queue.empty():
            self.objects_bucket = queue.get()

        return self.objects_bucket

    def run_no_dfs(self) -> dict:
        """Runs the fuzzer without using the dependency graph. Just uses each node and tests against the server

        Returns:
            dict: The objects bucket
        """
        nodes_to_run = self.dependency_graph.nodes
        self.__run_nodes(nodes_to_run)
        self.logger.info("Completed fuzzing")
        self.stats.print_results()
        self.stats.save()
        return self.objects_bucket

    def __run_steps(self, queue: multiprocessing.Queue):
        """Runs the fuzzer. Performs steps as follows:
        1. Gets all nodes that can be run without a dependency (query/mutation)
        2. 1st Pass: Perform DFS, going through only CREATE nodes and query nodes
        3. 2nd Pass: Perform DFS, allow UPDATE as well as CREATE and also query nodes
        4. 3rd Pass: Perform DFS, allow DELETE and UNKNOWN
        5. Get all nodes that still haven't been ran, run them (these are the nodes that may be in islands of the graph - very rare)
        6. Clean up

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

        # Step 6: Finish
        self.logger.info("Completed fuzzing")
        self.logger.info(f"Objects bucket: {self.objects_bucket}")
        self.stats.print_results()
        self.stats.save()
        queue.put(self.objects_bucket)

    def __run_nodes(self, nodes: list[Node]):
        """Runs the nodes given in the list

        Args:
            nodes (list[Node]): List of nodes to run

        Raises:
            Exception: If the GraphQL type of the node is unknown
        """
        for current_node in nodes:
            self.stats.print_running_stats()
            new_objects_bucket = self.objects_bucket
            self.logger.info(f"Running node: {current_node}")
            if current_node.graphql_type == "Query" or current_node.graphql_type == "Mutation":
                new_objects_bucket, _graphql_response, result = self.fengine.run_regular_payload(
                    current_node.name,
                    self.objects_bucket,
                    current_node.graphql_type,
                    check_hard_depends_on=False
                )
            elif current_node.graphql_type == "Object":
                continue
            else:
                raise Exception(f"Unknown GraphQL type: {current_node.graphql_type}")

            # Upddate the stats
            self.stats.update_stats_from_result(current_node, result)

            # If it was a success, then update the objects bucket
            if result.get_success():
                self.logger.info(f"Node was successful: {current_node}")
                self.objects_bucket = new_objects_bucket

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
                new_paths_to_evaluate, res = self.__evaluate_node(current_node, current_visit_path)     # For positive testing (normal run)
                self.__fuzz_node(current_node, current_visit_path)                                      # For negative testing (fuzzing)
                self.stats.update_stats_from_result(current_node, res)                                  # Update the stats

                # If it's not successful:
                # then we check if it's exceeded the max retries
                # If it is, then we dont re-queue the node
                if not res.get_success():
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

    def __evaluate_node(self, node: Node, visit_path: list[Node]) -> tuple[list[list[Node]], Result]:
        """Evaluates the node, performing the following based on the type of node
           Case 1: If it's an object node, then we should check if the object is in our bucket. If not, fail, if it is,
                   then queue up the next neighboring nodes to visit
           Case 2: If it's an query node or mutation node, run the payload with the required objects, then store the results in the object bucket

        Args:
            node (Node): Node to be evaluated
            visit_path (list[Node]): The list of visited paths to arrive at the node

        Returns:
            tuple[list[list[Node]], Result]: A list of the next to_visit paths, and the result of the node evaluation
        """
        neighboring_nodes = self._get_neighboring_nodes(node)
        new_visit_paths = self._get_new_visit_path_with_neighbors(neighboring_nodes, visit_path)

        if node.graphql_type == "Object":
            if node.name not in self.objects_bucket or len(self.objects_bucket[node.name]) == 0:
                return ([], Result.INTERNAL_FAILURE)
            else:
                return (new_visit_paths, Result.GENERAL_SUCCESS)
        else:
            new_objects_bucket, _graphql_response, res = self.fengine.run_regular_payload(
                node.name,
                self.objects_bucket,
                node.graphql_type,
                check_hard_depends_on=True
            )
            if res == Result.GENERAL_SUCCESS:
                self.objects_bucket = new_objects_bucket
                return (new_visit_paths, res)
            else:
                return ([], res)

    def __fuzz_node(self, node: Node, visit_path: list[Node]):
        """Fuzzes a node by running the node and storing the results. Currently runs:
           - DOS Query / Mutation (from size 0 to MAX_INPUT_DEPTH or HARD_CUTOFF_DEPTH, whichever is smaller)

        Args:
            node (Node): The node to fuzz
            visit_path (list[Node]): The list of visited paths to arrive at the node
        """
        # DOS Query / Mutation
        random_numbers = [random.randint(1, min(constants.HARD_CUTOFF_DEPTH, constants.MAX_INPUT_DEPTH)) for _ in range(0, constants.MAX_FUZZING_ITERATIONS)]
        for depth in random_numbers:
            if node.graphql_type in ["Query", "Mutation"]:
                self.logger.info(f"Running DOS {node.graphql_type}: {node.name} with depth: {depth}")
                new_objects_bucket, _graphql_response, res = self.fengine.run_dos_payload(node.name, self.objects_bucket, node.graphql_type, depth)
                self.stats.update_stats_from_result(node, res)

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
        return [random.choice(self.dependency_graph.nodes)]
