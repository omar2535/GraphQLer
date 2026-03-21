from typing import Any

def is_non_empty_result(value: Any) -> bool:
    """Checks if a GraphQL result contains any non-empty fields recursively.

    Args:
        value (Any): The value to check (dict, list, str, int, float, bool, etc.)

    Returns:
        bool: True if the result contains actual data, False if entirely empty/null.
    """
    if value is None:
        return False

    if isinstance(value, str):
        # bool("") is False, bool("text") is True. 
        # Note: use bool(value.strip()) if you want spaces like "   " to count as empty.
        return bool(value)

    if isinstance(value, dict):
        # any() automatically returns False if the dict is empty
        return any(is_non_empty_result(v) for v in value.values())

    if isinstance(value, list):
        # any() automatically returns False if the list is empty
        return any(is_non_empty_result(item) for item in value)

    # Fallback for ints, floats, and booleans (e.g., 0, 0.0, False).
    # In GraphQL/JSON, these represent actual data points, so they are non-empty.
    return True
