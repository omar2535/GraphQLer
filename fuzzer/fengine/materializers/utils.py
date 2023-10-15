import random


def get_random_string(input_name: str) -> str:
    # Maybe we can use the input name somehow? (Like if the input name contains "name")
    return '"Bob"'


def get_random_int(input_name: str) -> int:
    return 1


def get_random_float(input_name: str) -> float:
    return 3.1415


def get_random_bool(input_name: str) -> bool:
    return bool(random.getrandbits(1))


def get_random_id(input_name: str) -> str:
    return '"1234567890"'


# Gets a random scalar for the scalar type given
def get_random_scalar(input_name: str, scalar_type: str) -> str:
    """Gets a random scalar based on the scalar type, the return value will
       be a string regardless if of it's type as this function meant to be used
       during materialization

    Args:
        input_name (str): The input field's name
        scalar_type (str): The scalar type (IE. Int, Float, String, Boolean, ID, ect)

    Returns:
        str: The returned scalar
    """
    if scalar_type == "String":
        return get_random_string(input_name)
    elif scalar_type == "Int":
        return str(get_random_int(input_name))
    elif scalar_type == "Float":
        return str(get_random_float(input_name))
    elif scalar_type == "Boolean":
        return str(get_random_bool(input_name))
    elif scalar_type == "ID":
        return str(get_random_id(input_name))
    else:
        # Must be a custom scalar, skip for now
        raise Exception(f"Custom scalars are not supported at this time: {input_name}:{scalar_type}")


def get_random_enum_value(enum_values: list[dict]) -> str:
    """Gets a random enum from the enumValue list

    Args:
        enum_values (list[dict]): The enumValues list

    Returns:
        str: The name of the randomly chosen enum, or None if none was found
    """
    non_deprecated_enum_values = [enum for enum in enum_values if not enum.get("isDeprecated", False)]
    if non_deprecated_enum_values:
        enum = random.choice(non_deprecated_enum_values)
        return enum["name"]
    else:
        return None


def get_random_id_from_bucket(objects_bucket: dict) -> str:
    """Gets a random ID from the bucket, or just "" if there are no IDs in the bucket

    Args:
        objects_bucket (dict): Object bucket

    Returns:
        str: an ID
    """
    # If it's empty, just return a random ID
    if not objects_bucket:
        return get_random_id("")

    for i in range(0, 30):
        random_key = random.choice(objects_bucket.keys())
        random_object = random.choice(objects_bucket[random_key])
        if "id" in random_object:
            return random_object["id"]
    return get_random_id("")
