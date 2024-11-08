"""Getters module:
Used by the materializer to understand how to get values for fields
-- Can be overridden to provide custom values by different materializers (IE. DOS, Injection, ect)
"""

from datetime import datetime, timedelta
from graphqler.utils.objects_bucket import ObjectsBucket
import random
import string


class Getter:
    def __init__(self):
        pass

    def get_random_string(self, input_name: str) -> str:
        # Maybe we can use the input name somehow? (Like if the input name contains "name")
        if "email" in input_name:
            return f"\"{''.join(random.choices(string.ascii_lowercase, k=10))}@{''.join(random.choices(string.ascii_lowercase, k=10))}.com\""
        elif "name" in input_name:
            return f"\"{''.join(random.choices(string.ascii_uppercase + string.digits, k=10))}\""
        else:
            return f"\"{''.join(random.choices(string.ascii_uppercase + string.digits, k=10))}\""

    def get_random_int(self, input_name: str) -> int:
        return random.randint(0, 100)

    def get_random_float(self, input_name: str) -> float:
        if input_name == "latitude" or input_name == "longitude":
            return random.uniform(-180.0, 180.0)
        return random.uniform(0.0, 1000.0)

    def get_random_bool(self, input_name: str) -> str:
        return str(bool(random.getrandbits(1))).lower()

    def get_random_id(self, input_name: str, objects_bucket: ObjectsBucket) -> str:
        random_id = self.get_random_id_from_bucket(input_name, objects_bucket)
        if random_id.strip() == "":
            random_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        return '"' + str(random_id) + '"'

    def get_random_date(self, input_name: str) -> str:
        return f"\"{datetime.today().strftime('%Y-%m-%d')}\""

    def get_random_time(self, input_name: str) -> str:
        random_date_interval = random.randint(-10, 10)
        calculated_date = datetime.today() + timedelta(days=random_date_interval)
        return f"\"{calculated_date.strftime('%Y-%m-%d')}TT00:00:00+00:00\""

    def get_random_long(self, input_name: str) -> str:
        return str(random.randint(0, 1000000))

    def get_random_json(self, input_name: str) -> str:
        return "{}"

    def get_random_datetime(self, input_name: str) -> str:
        # Current datetime)
        now = datetime.now()
        # Range: 3 days before to 3 days after the current datetime
        start_date = now - timedelta(days=3)
        end_date = now + timedelta(days=3)

        # Calculate the total number of seconds in the range
        time_delta = end_date - start_date
        total_seconds = int(time_delta.total_seconds())

        # Generate a random number of seconds within the range
        random_seconds = random.randint(0, total_seconds)

        # Add the random seconds to the start date to get a random datetime
        random_date = start_date + timedelta(seconds=random_seconds)

        # Format the datetime in ISO 8601 format with a 'Z' suffix for UTC
        graphql_datetime = random_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        return f'"{graphql_datetime}"'

    # Gets a random scalar for the scalar type given
    def get_random_scalar(self, input_name: str, scalar_type: str, objects_bucket: ObjectsBucket) -> str:
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
            return self.get_random_string(input_name)
        elif scalar_type == "Int":
            return str(self.get_random_int(input_name))
        elif scalar_type == "Float":
            return str(self.get_random_float(input_name))
        elif scalar_type == "Boolean":
            return str(self.get_random_bool(input_name))
        elif scalar_type == "Date":
            return self.get_random_date(input_name)
        elif scalar_type == "ID":
            return self.get_random_id(input_name, objects_bucket)
        elif scalar_type == "Cursor":
            if input_name == "after" or input_name == "from":
                return "null"
            else:
                return str(1)
        else:
            # Must be a custom scalar, check if it's an ID, if not then just fail
            if scalar_type.lower().endswith("id") or scalar_type.lower().endswith("ids"):
                return str(self.get_random_id(input_name, objects_bucket))
            elif scalar_type.lower() == "time":
                return self.get_random_time(input_name)
            elif scalar_type.lower() == "long":
                return self.get_random_long(input_name)
            elif scalar_type.lower() == "datetime":
                return self.get_random_datetime(input_name)
            elif scalar_type.lower() == "json":
                return self.get_random_json(input_name)
            else:
                raise Exception(f"This custom scalar is not supported at this time: {input_name}:{scalar_type}")

    def get_random_enum_value(self, enum_values: list[dict]) -> str:
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
            raise Exception("No non-deprecated enum values found for this enum")

    def get_random_id_from_bucket(self, input_name: str, objects_bucket: ObjectsBucket) -> str:
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
        if objects_bucket.is_empty():
            return ""

        random_id = objects_bucket.get_random_scalar_from_bucket_by_type("ID")
        return str(random_id)

    def get_closest_value_to_input(self, input_name: str, object_name: str, objects_bucket: ObjectsBucket) -> str | int | float | bool:
        """Gets the closest value to the input name given the object name, the input name, and the objects bucket
        Args:
            input_name (str): The input name
            object_name (str): The object name
            objects_bucket (dict): The objects bucket

        Returns:
            str: The closest field name
        """
        # Get the object from the bucket
        found_value = objects_bucket.get_random_object_field_value(object_name, input_name)
        if found_value is not None:
            return found_value

        # Get the object name without the input name
        # IE. If the input name is "name" and the object name is "PersonName", the lookup name would be just 'name' in the object
        new_field_name = input_name.lower().replace(object_name.lower(), "").replace("_", "").replace(" ", "")

        # Try finding the value again
        found_value = objects_bucket.get_random_object_field_value(object_name, new_field_name)
        if found_value is not None:
            return found_value

        raise Exception(f"Could not find a value for the input name: {input_name} in the object: {object_name}")
