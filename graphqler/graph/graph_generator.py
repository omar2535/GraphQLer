"""GraphGenerator: Creates a networkx graph and stores it in a pickle file for use later on during fuzzing
The linker does the following:
- Serialize all the objects (Objects, Queries, Mutations, InputObjects, Enums)
- Generate a graph of object dependencies
- Attach queries to the object node
- Attach mutations related to the object node

!Note!: We decide to not link object-objects together here as it is not relevant for graph traversal
"""

from pathlib import Path
from graphqler.utils.file_utils import read_yaml_to_dict
from graphqler import config
from .node import Node
from .utils import draw_graph

import networkx


class GraphGenerator:
    def __init__(self, save_path: str):
        self.save_path = save_path
        self.compiled_queries_save_path = Path(save_path) / config.COMPILED_QUERIES_FILE_NAME
        self.compiled_objects_save_path = Path(save_path) / config.COMPILED_OBJECTS_FILE_NAME
        self.compiled_mutations_save_path = Path(save_path) / config.COMPILED_MUTATIONS_FILE_NAME
        self.dependency_graph_visualization_save_path = Path(save_path) / config.GRAPH_VISUALIZATION_OUTPUT

        self.compiled_queries = read_yaml_to_dict(self.compiled_queries_save_path)
        self.compiled_objects = read_yaml_to_dict(self.compiled_objects_save_path)
        self.compiled_mutations = read_yaml_to_dict(self.compiled_mutations_save_path)

        self.dependency_graph = networkx.DiGraph()

    def get_dependency_graph(self) -> networkx.DiGraph:
        """Runs the graph generator and returns the graph

        Returns:
            networkx.DiGraph: The directed graph
        """
        self.run()
        return self.dependency_graph

    def draw_dependency_graph(self):
        """Draws the dependency graph based on the GRAPH_VISUALIZATION_OUTPUT constant"""
        draw_graph(self.dependency_graph, self.dependency_graph_visualization_save_path)

    def run(self):
        """Generates the graph, creating nodes and creating edges between nodes.
        3 types of nodes (Objects, Queries, Mutations)
        """

        """1. Create query nodes"""
        query_nodes = {}
        for query_name, query_body in self.compiled_queries.items():
            query_nodes[query_name] = Node("Query", query_name, query_body)

        """2. Create mutation nodes"""
        mutation_nodes = {}
        for mutation_name, mutation_body in self.compiled_mutations.items():
            mutation_node = Node("Mutation", mutation_name, mutation_body)
            mutation_node.set_mutation_type(mutation_body["mutationType"])
            mutation_nodes[mutation_name] = mutation_node

        """3. Create object nodes"""
        object_nodes = {}
        for object_name, object_body in self.compiled_objects.items():
            object_nodes[object_name] = Node("Object", object_name, object_body)

        """4. Add all nodes to the graph"""
        self.dependency_graph.add_nodes_from(query_nodes.values())
        self.dependency_graph.add_nodes_from(mutation_nodes.values())
        self.dependency_graph.add_nodes_from(object_nodes.values())

        """5. Link objects and mutations together"""
        self.create_object_mutation_edges(object_nodes, mutation_nodes)

        """6. Link objects and queries together"""
        self.create_object_query_edges(object_nodes, query_nodes)

    def create_object_mutation_edges(self, object_nodes: dict, mutation_nodes: dict):
        """Updates the dependency graph with edges between objects and mutations. 3 cases:
           Case 1: M -> O | When object(O) depends on mutation(M), means O has M in its "associatedMutations", weight 100
           Case 2: O -> M | When mutation(M) depends on object(O), means M has O in its "hardDependsOn", weight 100
           Case 3: O -> M | When mutation(M) depends on object(O), means M has O in its "softDependsOn", weight 1

        Args:
            object_nodes (dict): Mapping of object_name -> object node
            mutation_nodes (dict): Mapping of mutation name -> mutation node
        """
        # Case 1
        for object_name, object_node in object_nodes.items():
            object_information = self.compiled_objects[object_name]
            if not object_information["associatedMutatations"]:
                continue  # skip if this object doesn't have any associated mutations

            for associated_mutation_name in object_information["associatedMutatations"]:
                mutation_node = mutation_nodes[associated_mutation_name]
                self.dependency_graph.add_edge(mutation_node, object_node, weight=100)

        # Case 2
        for mutation_name, mutation_node in mutation_nodes.items():
            mutation_information = self.compiled_mutations[mutation_name]
            if not mutation_information["hardDependsOn"]:
                continue  # skip if this mutation doesn't have any hardDependsOn

            if mutation_information["hardDependsOn"]:
                for input_name, object_name in mutation_information["hardDependsOn"].items():
                    if object_name != "UNKNOWN":
                        object_node = object_nodes[object_name]
                        self.dependency_graph.add_edge(object_node, mutation_node, weight=100)

        # Case 3
        for mutation_name, mutation_node in mutation_nodes.items():
            mutation_information = self.compiled_mutations[mutation_name]
            if not mutation_information["softDependsOn"]:
                continue  # skip if this mutation doesn't have any hardDependsOn

            if mutation_information["softDependsOn"]:
                for input_name, object_name in mutation_information["softDependsOn"].items():
                    if object_name != "UNKNOWN":
                        object_node = object_nodes[object_name]
                        self.dependency_graph.add_edge(object_node, mutation_node, weight=1)

    def create_object_query_edges(self, object_nodes: dict, query_nodes: dict):
        """Updates the dependency graph with edges in between objects and queries. 3 cases:
           Case 1: M -> O | When object(O) is produced by query(Q), means O has Q in its "associatedQueries", weight 100
           Case 2: O -> Q | When query(Q) depends on object(O), means Q has O in its "hardDependsOn", weight 100
           Case 3: O -> Q | When query(Q) depends on object(O), means Q has O in its "softDependsOn", weight 1

        Args:
            object_nodes (dict): Mapping of object_name -> object node
            query_nodes (dict): Mapping of query_name -> query node
        """
        # Case 1
        for object_name, object_node in object_nodes.items():
            object_information = self.compiled_objects[object_name]
            if not object_information["associatedQueries"]:
                continue  # skip if this object doesn't have any associatedQueries

            for associated_query_name in object_information["associatedQueries"]:
                query_node = query_nodes[associated_query_name]
                self.dependency_graph.add_edge(query_node, object_node, weight=100)

        # Case 2
        for query_name, query_node in query_nodes.items():
            query_information = self.compiled_queries[query_name]
            if not query_information["hardDependsOn"]:
                continue  # skip if this querry doesn't have any hardDependsOn

            for input_name, object_name in query_information["hardDependsOn"].items():
                if object_name != "UNKNOWN":
                    object_node = object_nodes[object_name]
                    self.dependency_graph.add_edge(object_node, query_node, weight=100)

        # Case 3
        for query_name, query_node in query_nodes.items():
            query_information = self.compiled_queries[query_name]
            if not query_information["softDependsOn"]:
                continue  # skip if this querry doesn't have any hardDependsOn

            for input_name, object_name in query_information["softDependsOn"].items():
                if object_name != "UNKNOWN":
                    object_node = object_nodes[object_name]
                    self.dependency_graph.add_edge(object_node, query_node, weight=1)
