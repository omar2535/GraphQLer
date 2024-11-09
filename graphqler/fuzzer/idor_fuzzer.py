"""Insecure direct object reference fuzzer"""

from graphqler.fuzzer.fuzzer import Fuzzer
from graphqler.graph import Node
from graphqler.utils.logging_utils import Logger
from graphqler.utils.objects_bucket import ObjectsBucket
from graphqler.fuzzer.engine.types.result import Result


class IDORFuzzer(Fuzzer):
    def __init__(self, path: str, url: str, objects_bucket: ObjectsBucket):
        """Iniitializes the IDOR fuzzer

        Args:
            path (str): The path to save the IDOR fuzzer
            url (str): The URL
            objects_bucket (dict): The objects bucket from a previous run
        """
        super().__init__(path, url)
        self.objects_bucket = objects_bucket

        # Override the default logger
        self.logger = Logger().get_idor_logger()
        self.fengine.logger = self.logger

    def run(self):
        """Runs the fuzzer

        Returns:
            dict: The objects bucket
        """
        self.logger.info("Starting IDOR Fuzzer")
        nodes_to_check: list[Node] = list(self.dependency_graph.nodes)
        possible_idor_nodes: list[Node] = []

        for node in nodes_to_check:
            result = self.check_node(node)
            if result:
                possible_idor_nodes.append(node)

        self.logger.info(f"Possible IDOR nodes: {possible_idor_nodes}")
        self.objects_bucket.save()

    def check_node(self, node: Node) -> bool:
        """Checks if a node has a possible IDOR vulnerability, if it does, return True, else False

        Args:
            node (Node): The node to be fuzzed

        Returns:
            bool: True if has suspected IDOR vulenrablity, False otherwise
        """
        if node.graphql_type == "Query" or node.graphql_type == "Mutation":
            graphql_response, result = self.fengine.run_minimal_payload(node.name, self.objects_bucket, node.graphql_type, check_hard_depends_on=False)
            if result == Result.HAS_DATA_SUCCESS:
                return True
        return False
