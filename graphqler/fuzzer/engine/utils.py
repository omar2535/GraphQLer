def check_is_data_empty(result: dict) -> bool:
    """Checks whether a response payload carries no usable data.

    A value counts as data when it is a non-None scalar, a dict holding data, or
    a list holding at least one element that itself holds data. An empty list is
    not data: the operation resolved, but returned no objects.
    """
    return all(_is_value_empty(value) for value in result.values())


def _is_value_empty(value) -> bool:
    """Checks a single response value, recursing through dicts and lists."""
    if isinstance(value, dict):
        return check_is_data_empty(value)
    if isinstance(value, list):
        return all(_is_value_empty(item) for item in value)
    return value is None
