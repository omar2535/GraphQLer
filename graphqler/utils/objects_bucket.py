"""Class for an objects bucket to contain the history of all objects in the system under test
"""

from graphqler.constants import USE_OBJECTS_BUCKET
from .singleton import singleton


@singleton
class ObjectsBucket:
    def __init__(self):
        self.bucket = {}

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
