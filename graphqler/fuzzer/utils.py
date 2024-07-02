from graphqler.constants import USE_OBJECTS_BUCKET
from graphqler.graph import Node
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


def put_in_object_bucket(objects_bucket: dict, object_name: str, object_val: str) -> dict:
    """Puts an object in the bucket, returns the new bucket. If the object already exists, it will not be added.

    Args:
        objects_bucket (dict): The objects bucket
        object_name (str): The objects name
        object_val (str): The objects value (for example ID)

    Returns:
        dict: The new bucket with the object_name: [..., object_val]
    """
    # If we're not using the objects bucket, just return an empty dict
    if not USE_OBJECTS_BUCKET:
        return {}

    if object_name in objects_bucket:
        if object_val not in objects_bucket[object_name]:
            objects_bucket[object_name].append(object_val)
    else:
        objects_bucket[object_name] = [object_val]
    return objects_bucket


def remove_from_object_bucket(objects_bucket: dict, object_name: str, object_val: str) -> dict:
    """Removes an object in the bucket, returns the new bucket. If the object doesn't exist, it will not be removed.

    Args:
        objects_bucket (dict): The objects bucket
        object_name (str): The objects name
        object_val (str): The objects value

    Returns:
        dict: The new bucket
    """
    # If we're not using the objects bucket, just return an empty dict
    if not USE_OBJECTS_BUCKET:
        return {}

    if object_name in objects_bucket:
        if object_val in objects_bucket[object_name]:
            objects_bucket[object_name].remove(object_val)
    return objects_bucket
