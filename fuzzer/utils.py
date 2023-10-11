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


def filter_mutation_paths(paths_to_evalute: list[list[Node]], filter_mutation_type: list[str]) -> list[list[Node]]:
    """Filter the mutations that aren't desired in the paths_to_evaluate

    Args:
        paths_to_evalute (list[list[Node]]): The paths to evaluate
        filter_mutation_type (list[str]): The mutation type to filter out

    Returns:
        list[list[Node]]: The filtered paths to evaluate
    """
    filtered_paths = []
    for path in paths_to_evalute:
        visit_node = path[-1]
        if visit_node.name == "Mutation" and visit_node.mutation_type in filter_mutation_type:
            pass
        else:
            filtered_paths.append(path)
    return filtered_paths


def put_in_object_bucket(objects_bucket: dict, object_name: str, object_val: str) -> dict:
    """Puts an object in the bucket, returns the new bucket

    Args:
        objects_bucket (dict): The objects bucket
        object_name (str): The objects name
        object_val (str): The objects value (for example ID)

    Returns:
        dict: The new bucket with the object_name: [..., object_val]
    """
    if object_name in objects_bucket:
        objects_bucket[object_name].append(object_val)
    else:
        objects_bucket[object_name] = [object_val]
    return objects_bucket
