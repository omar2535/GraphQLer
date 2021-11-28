import yaml
import networkx as nx

class GraphParser:
    
    dependency_graph = nx.DiGraph()

    # Constructor
    def __init__(self):
        pass
        
    def generate_dependency_graph(self, spec_path: str) -> nx.DiGraph:
        """Generates dependency graph from grammar specification

        Args:
            spec_path (String): Path of YAML file of the grammar

        Returns:
            networkx.DiGraph: Directed graph of methods that depends on each other 
        """
        grammar_contents = self.load_yaml(spec_path)
        self.parse_mutations(grammar_contents)
        self.parse_queries(grammar_contents)
        return self.dependency_graph
    
    # Loads yaml file from path
    def load_yaml(self, spec_path: str) -> None:
        with open(spec_path, "r") as stream:
            return yaml.safe_load(stream)

    # parse mutation dependencies
    def parse_mutations(self, grammar_contents) -> None:
        for mutation in grammar_contents['Mutations']:
            self.dependency_graph.add_node(mutation['name'])
            self.parse_depends_on(mutation)
    
    # parse query dependencies
    def parse_queries(self, grammar_contents) -> None:
        for query in grammar_contents['Queries']:
            self.dependency_graph.add_node(query['name'])
            self.parse_depends_on(query)

    # Parse depends_on of a method
    def parse_depends_on(self, method) -> None:
        if method['depends_on'] is None:
            return
        for dependency in method['depends_on']:
            self.dependency_graph.add_edge(method['name'], dependency)
