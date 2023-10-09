from graph import Node
import networkx


def get_node(graph: networkx.DiGraph, name: str) -> Node:
    """Gets a node from the graph with the same name

    Args:
        graph (networkx.DiGraph): The graph to look in
        name (str): The name of the node

    Returns:
        Node: A node matching the name, None if not found
    """
    for node in graph.nodes:
        if node.name == name:
            return node
    return None
