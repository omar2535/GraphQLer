"""
Utilities that will come in handy when parsing the various dictionaries
"""


def get_base_oftype(oftype: dict) -> dict:
    """Gets the base oftype from a NON_NULL/LIST oftype (recursively goes down)

    Args:
        oftype (dict): Oftype to get

    Returns:
        dict: the base oftype with kind, name, and ofType
    """
    if "ofType" in oftype and oftype["ofType"] is not None:
        return get_base_oftype(oftype["ofType"])
    else:
        return oftype


def get_output_type(payload_name: str, mutations: dict) -> str:
    """Gets the mutation/query's output type. If it's a SCALAR, just returns the name of the field
       If it's an object, returns the Object's name

    Args:
        payload_name (str): The name of either the mutation or query
        mutations (dict): The mutations in this API

    Returns:
        str: The output name
    """
    mutation_info = mutations[payload_name]
    if mutation_info["output"]["ofType"] is not None:
        type_to_parse = get_base_oftype(mutation_info["output"]["ofType"])
    else:
        type_to_parse = mutation_info["output"]

    if type_to_parse["kind"] == "OBJECT":
        return type_to_parse["type"]
    else:
        return type_to_parse["name"]
