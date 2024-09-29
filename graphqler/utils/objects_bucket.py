"""Class for an objects bucket to contain the history of all objects in the system under test
"""

from graphqler.constants import USE_OBJECTS_BUCKET
from .singleton import singleton
import random
import pprint


@singleton
class ObjectsBucket:
    def __init__(self):
        self.bucket = {}

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

    def put_in_bucket(self, name: str, val: str) -> dict:
        """Puts an object in the bucket, returns the new bucket. If the object already exists, it will not be added.

        Args:
            name (str): The objects name
            val (str): The objects value (for example ID)

        Returns:
            dict: The new bucket with the object_name: [..., object_val]
        """
        # If we're not using the objects bucket, just return an empty dict
        if not USE_OBJECTS_BUCKET:
            return {}

        if name in self.bucket:
            self.bucket[name].add(val)
        else:
            self.bucket[name] = set([val])
        return self.bucket

    def remove_from_object_bucket(self, name: str, val: str) -> dict:
        """Removes an object in the bucket, returns the new bucket. If the object doesn't exist, it will not be removed.

        Args:
            name (str): The objects name
            val (str): The objects value

        Returns:
            dict: The new bucket
        """
        # If we're not using the objects bucket, just return an empty dict
        if not USE_OBJECTS_BUCKET:
            return {}

        if name in self.bucket:
            if val in self.bucket[name]:
                self.bucket[name].remove(val)
        return self.bucket

    def get_closest_key_to_bucket(self, input_name: str, objects_bucket: dict) -> str:
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

    def get_random_id_from_bucket(self, input_name: str, objects_bucket: dict) -> str:
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

        key = self.get_closest_key_to_bucket(input_name, objects_bucket)
        random_object = random.choice(objects_bucket[key])
        return f'"{random_object}"'
