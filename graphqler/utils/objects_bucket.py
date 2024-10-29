"""Class for an objects bucket to contain the history of all objects in the system under test
What does an objects bucket track?
- For each type of object, track any values that were associated to that object to be used later
- For each kind of scalar, track any values seen to be used later

TODO: Implement the following:
The class should have two functionalities
1. Given the graphql data response, parse the data and put objects in the bucket
2. Be able to return random scalars / objects from the bucket
3. Be able to return objects from the bucket if given a type and the object name
"""

from graphqler.constants import USE_OBJECTS_BUCKET
from .singleton import singleton
from graphqler.utils.api import API
from graphqler.utils.parser_utils import get_output_type_from_details
import pprint

import random


@singleton
class ObjectsBucket:
    def __init__(self, api: API):
        self.api = api

        # Stores {object_name: {type: str, results: dict}} where list is a result with the scalar fields of the object
        self.objects: dict[str, list] = {}

        # Stores the raw scalars {scalar_name: {type: str, values: set() }} where set() is a result with the scalar fields of the object
        self.scalars: dict[str, dict] = {}

    def __str__(self):
        """Returns a string representation of the objects bucket"""
        built_str = "\n------------------- OBJECTS BUCKET -------------------\n"
        built_str += pprint.pformat(self.objects)

        built_str += "\n------------------- SCALARS BUCKET -------------------\n"
        built_str += pprint.pformat(self.scalars)

        return built_str

    def __getstate__(self):
        # Return a dictionary of the attributes to pickle
        return self.__dict__

    def __setstate__(self, state):
        # Restore the state from the pickled attributes
        self.__dict__.update(state)

    # ------------------- GETTERS -------------------
    def get_random_object(self, object_name: str) -> dict:
        """Returns a random object from the bucket

        Args:
            object_name (str): The object name

        Returns:
            dict: A random object from the bucket
        """
        if object_name not in self.objects:
            return {}

        return next(iter(self.objects[object_name]))

    def get_random_object_field_value(self, object_name: str, field_name: str) -> str | int | float | bool | None:
        """Returns a random field from an object

        Args:
            object_name (str): The object name
            field_name (str): The field name

        Returns:
            str | int | float | bool: The field value
        """
        if object_name not in self.objects:
            raise Exception("Object not found in bucket")

        random_index = random.randint(0, len(self.objects[object_name]) - 1)
        object_to_use = self.objects[object_name][random_index]
        found_key, found_value = self.find_key_in_dict(object_to_use, field_name)

        if found_value is None:
            return None
        return found_value

    # ------------------- SETTERS -------------------
    def put_in_bucket(self, response_data: dict) -> bool:
        """Puts an object in the bucket, returns True if the object was added, False otherwise

        Args:
            response_data (dict): The data to put in the bucket. This is the responses data from GraphQL

        Returns:
            bool: True if the object was added, False otherwise
        """
        # If we're not using the objects bucket, just return an empty dict
        if not USE_OBJECTS_BUCKET:
            return False

        # If no data, just return
        if not response_data:
            return False

        # Iterate through the data, put in the bucket
        for data_key, data in response_data.items():
            if self.api.is_operation_in_api(data_key):
                self.parse_as_object(data_key, data)
            # Regardless, always parse the entire data into our scalars bucket as well for future lookups
            self.parse_as_scalar(data_key, data)
        return True

    def parse_as_object(self, operation_name: str, data: dict | list[dict]):
        """Parses the data as an object by looking up the output of the operation in the API

        Args:
            operation_name (str): The operation name, should be an operation in the API
            data (dict | List[dict]): The data to parse
        """
        # Get the operation from the API
        operation = self.api.get_operation(operation_name)
        operation_output_type = get_output_type_from_details(operation)

        if isinstance(data, list):
            for item in data:
                self.put_object_in_bucket(operation_output_type, item)
        else:
            self.put_object_in_bucket(operation_output_type, data)

    def parse_as_scalar(self, method_name: str, method_data: dict | list | str | int | float | bool | None):
        """Parses the data as a scalar (can be a list, dict, or any of the base GraphQL types

        Args:
            method_name (str): The method name
            method_data (str): The method data
        """
        if isinstance(method_data, str):
            self.put_scalar_in_bucket(method_name, "String", method_data)
        elif isinstance(method_data, bool):
            self.put_scalar_in_bucket(method_name, "Boolean", method_data)
        elif isinstance(method_data, int):
            self.put_scalar_in_bucket(method_name, "Int", method_data)
        elif isinstance(method_data, float):
            self.put_scalar_in_bucket(method_name, "Float", method_data)
        elif isinstance(method_data, list):
            for item in method_data:
                self.parse_as_scalar(method_name, item)
        elif isinstance(method_data, dict):
            self.parse_object_scalars(method_data)

    def put_object_in_bucket(self, object_name: str, object_info: dict):
        """Puts an object in the bucket

        Args:
            object_name (str): The object's name
            object_info (dict): The object's info
        """
        if object_name not in self.objects:
            self.objects[object_name] = []
        self.objects[object_name].append(object_info)

    def parse_object_scalars(self, object_info: dict):
        """Parses each field of a dictionary as a scalar and parses it into the scalar components

        Args:
            object_info (dict): The object info
        """
        for field_name, field_value in object_info.items():
            self.parse_as_scalar(field_name, field_value)

    def put_scalar_in_bucket(self, name: str, type: str, data: str | int | float | bool):
        """Puts scalar in the bucket

        Args:
            name (str): The scalar's name
            type (str): The scalar's type
            data (str): The scalar's data
        """
        if name not in self.scalars:
            self.scalars[name] = {"type": type, "values": {data}}
        self.scalars[name]["values"].add(data)

    # ------------------- DELETERS -------------------
    def delete_object_from_bucket(self, object_name: str):
        """Deletes an object from the bucket

        Args:
            object_name (str): The object name
        """
        # TODO: Need to figure out what to remove from bucket since
        #       there will be many objects under the object name
        pass

    # ------------------- HELPERS -------------------
    def clear_bucket(self):
        """Clears the bucket"""
        self.objects.clear()
        self.scalars.clear()

    def is_empty(self) -> bool:
        """Checks if the object bucket is empty

        Returns:
            bool: True if the object bucket is empty, False otherwise
        """
        return len(self.objects) == 0 and len(self.scalars) == 0

    def is_object_in_bucket(self, object_name: str) -> bool:
        """Checks if an object is in the bucket

        Args:
            object_name (str): The object name

        Returns:
            bool: True if the object is in the bucket, False otherwise
        """
        return object_name in self.objects and len(self.objects[object_name]) > 0

    def find_key_in_dict(self, dictionary: dict, key: str) -> tuple[str, str | int | float | bool | None]:
        """Recursively searches for the key in a nested dictionary and returns its full path and value.

        Args:
            dictionary (dict): The dictionary to search
            key (str): The key to search for

        Returns:
            tuple[str, str | int | float | bool | None]: The key and value

        """
        for k, v in dictionary.items():
            if k == key:
                return k, v
            if isinstance(v, dict):
                result = self.find_key_in_dict(v, key)
                if result is not None:
                    return result
        return ("", None)

    def get_random_scalar_from_bucket_by_type(self, scalar_type: str) -> str | int | float | bool:
        """Gets a random scalar from the bucket

        Args:
            scalar_type (str): The scalar type

        Returns:
            str | int | float | bool: The scalar value
        """
        for scalar_name, scalar in self.scalars.items():
            if scalar["type"] == scalar_type:
                return random.choice(list(scalar["values"]))
        return ""

    def get_random_scalar_from_bucket_by_name(self, scalar_name) -> str | int | float | bool:
        """Gets a random scalar from the bucket with the name

        Args:
            scalar_name (str): The scalar name

        Returns:
            str | int | float | bool: The scalar value
        """
        if scalar_name not in self.scalars:
            return ""

        return random.choice(list(self.scalars[scalar_name]["values"]))
