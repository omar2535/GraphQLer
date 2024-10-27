"""Utilities used on the output portion of the payload"""

import re
from graphql import parse, print_ast


def is_valid_object_materialization(materialized_str: str) -> bool:
    """Checks if the output is a valid object output
       Format: OBJECT_NAME(INPUT){OUTPUT}
       IE: - abc {} -> False
           - abc(filter:1) {} -> False
           - abc(filter: {def: 123}) {} -> False
           - abc(filter: {def: 123}) {def } -> True
           - abc {def} -> True
           - abc {, , ,} -> False

    Args:
        output_str (str): The string that is supposed to be output

    Returns:
        bool: Whether the output string is valid or not
    """
    # Cleaned string
    materialized_str = materialized_str.replace(" ", "")
    materialized_str = remove_consecutive_characters(materialized_str, ",")
    materialized_str = materialized_str.strip(",")
    if "{}" in materialized_str or "{,}" in materialized_str:
        return False

    # Parse the AST for validity of the payload
    try:
        dummy_payload = f"query STUFF{{{materialized_str}}}"
        parsed_obj = parse(dummy_payload)
        print_ast(parsed_obj).strip()
        return True
    except Exception:
        return False


def clean_output_selectors(output_selectors: str) -> str:
    """Cleans the output selectors by doing the following:L
       - Removing any extra commas
       - Removing Removing keys that don't have an object (ie. {stuff {}, otherstuff} -> {otherstuff})

    Args:
        output_selectors (str): _description_

    Returns:
        str: _description_
    """
    # Removing any extra commas
    while ",," in output_selectors:
        output_selectors = output_selectors.replace(",,", ",")

    # Removing keys that don't have an object
    while "{}" in output_selectors:
        output_selectors = output_selectors.replace("{},", "")
        output_selectors = output_selectors.replace(",{}", "")

    return output_selectors


def remove_consecutive_characters(s: str, char: str) -> str:
    """Removes consecutive occurrences of a specified character in a string,
    reducing them to a single occurrence of the character.

    Args:
        s (str): The input string.
        char (str): The character to reduce consecutive occurrences of.

    Returns:
        str: The modified string with consecutive characters reduced.
    """
    return re.sub(f"{char}+", char, s)


def prettify_graphql_payload(payload: str) -> str:
    """Uses graphql-core to prettify the payload

    Args:
        payload (str): The QUERY or MUTATION as a string

    Returns:
        str: A string of the formatted graphql payload
    """
    parsed_query = parse(payload)
    formatted_query = print_ast(parsed_query).strip()
    return formatted_query
