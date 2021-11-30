import yaml
import networkx as nx

from graphqler_types.graphql_request import GraphqlRequest

POSSIBLE_QUERY_TYPES = {"Mutations": "mutation", "Queries": "query"}


class GraphParser:

    dependency_graph = nx.DiGraph()

    # Constructor
    def __init__(self):
        pass

    def generate_dependency_graph(self, spec_path: str) -> nx.DiGraph:
        """
        Generates dependency graph from grammar specification.
        !Assumes that request method names are unique!

        Args:
            spec_path (String): Path of YAML file of the grammar

        Returns:
            networkx.DiGraph: Directed graph of methods that depends on each other
        """
        grammar_contents = self.load_yaml(spec_path)
        self.parse_nodes(grammar_contents)
        self.parse_dependencies()
        return self.dependency_graph

    # Loads yaml file from path
    def load_yaml(self, spec_path: str) -> None:
        with open(spec_path, "r") as stream:
            return yaml.safe_load(stream)

    # Creates node in grpah from the methods
    def parse_nodes(self, grammar_contents) -> None:
        for query_type_plural, query_type_singlular in POSSIBLE_QUERY_TYPES.items():
            for gql_request in grammar_contents[query_type_plural]:
                graphql_request = self.parseGraphqlRequestObject(gql_request, query_type_singlular)
                self.dependency_graph.add_node(graphql_request)

    # Creates edges in the graph from method dependencies
    def parse_dependencies(self) -> None:
        for node in list(self.dependency_graph.nodes):
            for method_name in node.depends_on:
                dependency = self.searchForNodeInGraph(method_name)
                self.dependency_graph.add_edge(node, dependency)

    # Creates a graphql request object from the yaml file
    def parseGraphqlRequestObject(self, gql_request, query_type) -> GraphqlRequest:
        name = gql_request["name"]
        depends_on = gql_request["depends_on"] or []
        params = gql_request["consumes"]
        graphql_request = GraphqlRequest(query_type, name, None, depends_on=depends_on, params=params)
        return graphql_request

    # Finds a node in the graph
    def searchForNodeInGraph(self, method_name) -> GraphqlRequest:
        for node in list(self.dependency_graph.nodes):
            if node.name == method_name:
                return node
        raise f"Couldn't find node in graph with method name: {method_name}"

    # Parse depends_on of a method
    def parse_depends_on(self, method) -> None:
        if method["depends_on"] is None:
            return
        for dependency in method["depends_on"]:
            self.dependency_graph.add_edge(method["name"], dependency)
