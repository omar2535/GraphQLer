"""Insecure direct object reference fuzzer"""

from fuzzer.fuzzer import Fuzzer
from graph import Node
from utils.logging_utils import Logger


class IDORFuzzer(Fuzzer):
    def __init__(self, path: str, url: str, objects_bucket: dict):
        """Iniitializes the IDOR fuzzer

        Args:
            path (str): The path to save the IDOR fuzzer
            url (str): The URL
            objects_bucket (dict): The objects bucket from a previous run
        """
        super().__init__(path, url)
        self.objects_bucket = objects_bucket

    def run(self) -> dict:
        """Runs the fuzzer

        Returns:
            dict: The objects bucket
        """
        self.logger.info("Starting IDOR Fuzzer")
        nodes_to_check: list[Node] = self.dependency_graph.nodes
        for node in nodes_to_check:
            self.check_node(node)

    def check_node(self, node: Node) -> bool:
        """Checks if a node has a possible IDOR vulnerability, if it does, return True, else False

        Args:
            node (Node): The node to be fuzzed

        Returns:
            bool: True if has suspected IDOR vulenrablity, False otherwise
        """
        if node.graphql_type == "Query":
            _objects_bucket, graphql_response, result = self.fengine.run_regular_query(node.name, self.objects_bucket, check_hard_depends_on=False)
            breakpoint()
        elif node.graphql_type == "Mutation":
            _objects_bucket, graphql_response, result = self.fengine.run_regular_mutation(node.name, self.objects_bucket, check_hard_depends_on=False)
            breakpoint()
        elif node.graphql_type == "Object":
            self.logger.info("Not checking object")

        return False
