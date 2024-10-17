import networkx

from graphqler.graph import Node


def get_node(graph: networkx.DiGraph, name: str) -> Node:
    """Gets a node from the graph with the same name

    Args:
        graph (networkx.DiGraph): The graph to look in
        name (str): The name of the node

    Returns:
        Node: A node matching the name. Raises exception if node isn't found
    """
    for node in graph.nodes:
        if node.name == name:
            return node
    raise Exception(f"Node with name {name} not found in graph")
