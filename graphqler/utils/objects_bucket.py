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


@singleton
class ObjectsBucket:
    def __init__(self, api: API):
        self.bucket = {}
        self.api = api

        # Stores {object_name: {type: str, results: dict}} where set() is a result with the scalar fields of the object
        self.objects: dict[str, set] = {}

        # Stores the raw scalars {scalar_name: {type: str, values: set() }} where set() is a result with the scalar fields of the object
        self.scalars: dict[str, dict] = {}

    def __str__(self):
        return pprint.pformat(self.bucket)

    def is_object_in_bucket(self, name: str) -> bool:
        """Checks if the object is in the bucket

        Args:
            name (str): The objects name

        Returns:
            bool: True if the object is in the bucket, False otherwise
        """
        return name in self.bucket

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
            self.objects[object_name] = set()

        self.objects[object_name].add(object_info)

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
