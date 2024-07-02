from graphql import parse, print_ast
from datetime import datetime, timedelta
import random
import string
import Levenshtein


def get_random_string(input_name: str) -> str:
    # Maybe we can use the input name somehow? (Like if the input name contains "name")
    if "email" in input_name:
        return f"\"{''.join(random.choices(string.ascii_lowercase, k=10))}@{''.join(random.choices(string.ascii_lowercase, k=10))}.com\""
    elif "name" in input_name:
        return f"\"{''.join(random.choices(string.ascii_uppercase + string.digits, k=10))}\""
    else:
        return f"\"{''.join(random.choices(string.ascii_uppercase + string.digits, k=10))}\""


def get_random_int(input_name: str) -> int:
    return random.randint(0, 100)


def get_random_float(input_name: str) -> float:
    if input_name == "latitude" or input_name == "longitude":
        return random.uniform(-180.0, 180.0)
    return random.uniform(0.0, 1000.0)


def get_random_bool(input_name: str) -> bool:
    return str(bool(random.getrandbits(1))).lower()


def get_random_id(input_name: str) -> str:
    return '"' + "".join(random.choices(string.ascii_uppercase + string.digits, k=10)) + '"'


def get_random_date(input_name: str) -> str:
    return f"\"{datetime.today().strftime('%Y-%m-%d')}\""


def get_random_time(input_name: str) -> str:
    random_date_interval = random.randint(-10, 10)
    calculated_date = datetime.today() + timedelta(days=random_date_interval)
    return f"\"{calculated_date.strftime('%Y-%m-%d')}TT00:00:00+00:00\""


def get_random_long(input_name: str) -> str:
    return str(random.randint(0, 1000000))


# Gets a random scalar for the scalar type given
def get_random_scalar(input_name: str, scalar_type: str, objects_bucket: dict) -> str:
    """Gets a random scalar based on the scalar type, the return value will
       be a string regardless if of it's type as this function meant to be used
       during materialization

    Args:
        input_name (str): The input field's name
        scalar_type (str): The scalar type (IE. Int, Float, String, Boolean, ID, ect)
        objects_bucket (dict): The objects bucket to look up for any random IDs we want to choose

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
    elif scalar_type == "Date":
        return get_random_date(input_name)
    elif scalar_type == "ID":
        random_id = get_random_id_from_bucket(input_name, objects_bucket)
        if random_id == "":
            random_id = str(get_random_id(input_name))
        return random_id
    elif scalar_type == "Cursor":
        if input_name == "after" or input_name == "from":
            return "null"
        else:
            return str(1)
    else:
        # Must be a custom scalar, check if it's an ID, if not then just fail
        if scalar_type.lower().endswith("id") or scalar_type.lower().endswith("ids"):
            random_id = get_random_id_from_bucket(input_name, objects_bucket)
            if random_id == "":
                random_id = str(get_random_id(input_name))
            return random_id
        elif scalar_type.lower() == "time":
            return get_random_time(input_name)
        elif scalar_type.lower() == "long":
            return get_random_long(input_name)
        else:
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


def get_random_id_from_bucket(input_name: str, objects_bucket: dict) -> str:
    """Tries to get an ID from the bucket based on the input_name first, then just randomly chooses an ID from the bucket,
       if the bucket is empty, then just returns an empty string
    Gets a random ID from the bucket, or just "" if there are no IDs in the bucket

    Args:
        input_name (str): The input name
        objects_bucket (dict): Object bucket

    Returns:
        str: an ID
    """
    # If it's empty, just return a random ID
    if not objects_bucket:
        return ""

    key = get_closest_key_to_bucket(input_name, objects_bucket)
    random_object = random.choice(objects_bucket[key])
    return f'"{random_object}"'


def get_closest_key_to_bucket(input_name: str, objects_bucket: dict) -> str:
    """Tries to find the object name if it has ID behind, if not, then chooses at random

    Args:
        input_name (str): The input name
        objects_bucket (dict): The objects bucket

    Returns:
        str: The key of the object
    """
    # Tries for the object name
    if input_name.endswith("Id"):
        object_name = input_name[0].capitalize() + input_name[1:-2]
        if object_name in objects_bucket:
            return object_name

    # Gives up and gets a key
    return random.choice(list(objects_bucket.keys()))


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
