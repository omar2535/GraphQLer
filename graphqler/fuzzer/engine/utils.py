def check_is_data_empty(result: dict) -> bool:
    for value in result.values():
        if isinstance(value, dict):
            if not check_is_data_empty(value):
                return False
        elif value is not None:
            return False
    return True
