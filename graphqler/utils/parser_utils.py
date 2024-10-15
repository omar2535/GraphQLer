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


def get_output_type(operation_name: str, operations: dict) -> str:
    """Gets the mutation/query's output type. If it's a SCALAR, just returns the name of the field
       If it's an object, returns the Object's name

    Args:
        payload_name (str): The name of either the mutation or query
        payloads (dict): QUERIES or MUTATIONS in this API

    Returns:
        str: The output name
    """
    payload_info = operations[operation_name]
    if payload_info["output"]["ofType"] is not None:
        type_to_parse = get_base_oftype(payload_info["output"]["ofType"])
    else:
        type_to_parse = payload_info["output"]

    if type_to_parse["kind"] == "OBJECT":
        return type_to_parse["type"]
    else:
        return type_to_parse["name"]


def get_output_type_from_details(operation_details: dict) -> str:
    """Gets the output type from the operation details

    Args:
        operation_details (str): The operation details

    Returns:
        str: The output type
    """
    if operation_details["output"]["ofType"] is not None:
        type_to_parse = get_base_oftype(operation_details["output"]["ofType"])
    else:
        type_to_parse = operation_details["output"]

    if type_to_parse["kind"] == "OBJECT":
        return type_to_parse["type"]
    else:
        return type_to_parse["name"]
