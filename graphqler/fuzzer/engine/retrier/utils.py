"""
Utilities for the retrier
"""

import re


def find_block_end(payload: str, line_number: int) -> int:
    """Finds the end line number for a block given a query or mutation.
       The query or mutation must be formatted with trailing curly braces and elements on their
       own lines.
       Cases:
         - when it's an object
         - when it's just an element

    Args:
        payload (str): The payload either a mutation or query
        line_number (int): The line number where we want to find the block

    Returns:
        int: Where the block ends
    """

    lines = payload.split("\n")
    if lines[line_number][-1] == "{":
        target_indentation = len(re.match(r"^\s*", lines[line_number]).group(0))
        current_line_number = line_number + 1
        current_indentation = len(re.match(r"^\s*", lines[current_line_number]).group(0))
        while current_indentation > target_indentation:
            current_line_number += 1
            current_indentation = len(re.match(r"^\s*", lines[current_line_number]).group(0))
        return current_line_number
    else:
        return line_number


def remove_lines_within_range(payload: str, start_line: int, end_line: int) -> str:
    """Removes lines within a range from start_line to end_line inclusive.
       The query or mutation must be formatted with trailing curly braces and elements on their
       own lines.

    Args:
        payload (str): The payload (either a query or mutation)
        start_line (int): The starting line number
        end_line (int): The end line number

    Returns:
        str: _description_
    """
    lines = payload.split("\n")
    new_lines = lines[0:start_line] + lines[end_line + 1 :]
    return "\n".join(new_lines)
