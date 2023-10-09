"""Class for fuzzer

1. Gets all nodes that can be run without a dependency (query/mutation)
2. Adds these to the DFS queue
3. 1st Pass: Perform DFS, going through only creation nodes
4. 2nd Pass: Perform DFS, allow also queries and updates
5. 3rd Pass: Perform DFS, allow deletions
6. Clean up
"""

from pathlib import Path
from graph import GraphGenerator, Node
from utils.file_utils import read_yaml_to_dict
from fuzzer.utils import get_node

import constants
import networkx


class Fuzzer:
    def __init__(self, save_path: str, url: str):
        """Initializes the fuzzer, reading information from the compiled files

        Args:
            save_path (str): Save directory path
            url (str): URL for graphql introspection query to hit
        """
        self.save_path = save_path
        self.url = url

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

        self.objects_bucket = {}

    def run(self):
        """Runs the fuzzer. Performs steps as follows:
        1. Gets all nodes that can be run without a dependency (query/mutation)
        2. Adds these to the DFS queue
        3. 1st Pass: Perform DFS, going through only creation nodes and query nodes
        4. 2nd Pass: Perform DFS, allow updates as well as creation and query nodes
        5. 3rd Pass: Perform DFS, allow deletions
        6. Clean up
        """
        # Step 1
        starter_nodes: list[Node] = self.get_non_dependent_nodes()

        # Step 2
        self.perform_dfs(starter_stack=starter_nodes)

    def get_non_dependent_nodes(self) -> list[Node]:
        """Gets all non-dependent nodes (nodes that don't have any edges going in
           Note: We choose to "include" any that have UNKNOWNS as they will fail during DFS execution anyways.
                 This getting non_dependency is simply based on the program's "world view"

        Returns:
            list[Node]: List of Nodes that don't require any pre-existing objects
        """

        in_degree_centrality = networkx.in_degree_centrality(self.dependency_graph)
        non_dependent_nodes = [node for node, centrality in in_degree_centrality.items() if centrality == 0]
        return non_dependent_nodes

    def perform_dfs(self, starter_stack: list[Node]):
        """Performs DFS with the initial starter stack

        Args:
            starter_stack (list[Node]): A list of the nodes to start the fuzzing
        """
        visited: list[Node] = []
        to_visit: list[list[Node]] = [[n] for n in starter_stack]
        while len(to_visit) != 0:
            current_visit_path: list[Node] = to_visit.pop()
            current_node: Node = current_visit_path[-1]
            if current_node not in visited:
                new_paths_to_evaluate, was_successful = self.evaluate_node(current_node, ["UPDATE", "DELETE"])
                if not was_successful:
                    to_visit.insert(0, current_visit_path)  # Will retry later, put it at the back of the stack
                else:
                    to_visit.extend(new_paths_to_evaluate)  # Will keep going deeper, put it at the front of the stack
                    visited.append(current_node)  # Add this to visited

    def evaluate_node(self, node: Node, avoid_mutation_type: list[str]) -> tuple[list[list[Node]], bool]:
        """Evaluates the node, performing the following based on the type of node
           Case 1: If it's an object node, then we simply add back up the mutations / queries
                   where their pre-conditions are already satisfied
           Case 2: If it's an query node, run the query with the required objects, then store in the object bucket
           Case 3: If it's a mutation node, run the mutation with the required objects

        Args:
            node (Node): Node to be evaluatred
            avoid_mutation_type (list[str]): Mutation types to avoid when looking for the next nodes to append

        Returns:
            tuple[list[list[Node]], bool]: A list of the next to_visit paths, and the bool if the node evaluation was successful or not
        """
