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


def get_mutation_output_type(mutation_name: str, mutations: dict) -> str:
    """Gets the mutation's output type. If it's a SCALAR, just returns the name of the field
       If it's an object, returns the Object's name

    Args:
        mutation_name (str): The mutation name
        mutations (dict): The mutations in this API

    Returns:
        str: The output name
    """
    mutation_info = mutations[mutation_name]
    if mutation_info["output"]["ofType"] is not None:
        type_to_parse = get_base_oftype(mutation_info["output"]["ofType"])
    else:
        type_to_parse = mutation_info["output"]

    if type_to_parse["kind"] == "OBJECT":
        return type_to_parse["type"]
    else:
        return type_to_parse["name"]
