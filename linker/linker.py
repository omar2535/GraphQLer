"""Linker: Creates a networkx graph and stores it in a pickle file for use later on during fuzzing
The linker does the following:
- Serialize all the objects (Objects, Queries, Mutations, InputObjects, Enums)
- Generate a graph of object dependencies
- Attach queries to the object node
- Attach mutations related to the object node
"""

from pathlib import Path
from .serializers import ObjectsSerializer
from utils.file_utils import read_yaml_to_dict
from graph.node import Node
from graph.utils import draw_graph

import constants
import networkx


class Linker:
    def __init__(self, save_path: str):
        self.save_path = save_path
        self.compiled_queries_save_path = Path(save_path) / constants.COMPILED_QUERIES_FILE_NAME
        self.compiled_objects_save_path = Path(save_path) / constants.COMPILED_OBJECTS_FILE_NAME
        self.compiled_mutationss_save_path = Path(save_path) / constants.COMPILED_MUTATIONS_FILE_NAME
        self.dependency_graph_visualization_save_path = Path(save_path) / constants.GRAPH_VISUALIZATION_OUTPUT

        self.compiled_queries = read_yaml_to_dict(self.compiled_queries_save_path)
        self.compiled_objects = read_yaml_to_dict(self.compiled_objects_save_path)
        self.compiled_mutations = read_yaml_to_dict(self.compiled_mutationss_save_path)

    def run(self):
        """Generater the NX graph and saave it as a pickle"""
        """0. Generate an empty graph"""
        dependency_graph = networkx.DiGraph()

        """1. Create query nodes"""
        query_nodes = []
        for query_name, query_body in self.compiled_queries.items():
            query_nodes.append(Node("Query", query_name, query_body))

        """2. Create mutation nodes"""
        mutation_nodes = []
        for mutation_name, mutation_body in self.compiled_mutations.items():
            mutation_nodes.append(Node("Mutation", mutation_name, mutation_body))

        """3. Create object nodes"""
        object_nodes = []
        for object_name, object_body in self.compiled_objects.items():
            object_nodes.append(Node("Object", object_name, object_body))

        """4. Add all nodes to the graph"""
        dependency_graph.add_nodes_from(query_nodes)
        dependency_graph.add_nodes_from(mutation_nodes)
        dependency_graph.add_nodes_from(object_nodes)

        """5. Link objects and mutations together"""
        pass

        """6. Link objects and queries together"""
        pass

        """7. Link objects and objects together"""
        pass

        """8. Write the networkx graph to a picke file"""
        pass

        """9. Draw the graph as well"""
        draw_graph(dependency_graph, self.dependency_graph_visualization_save_path)
