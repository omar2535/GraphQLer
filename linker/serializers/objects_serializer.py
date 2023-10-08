"""
Object serializer: serialize all compiled objects into a dictionary of object_name -> object pair
"""

from pathlib import Path
from utils.file_utils import read_yaml_to_dict
from graphqler_types import Object, Field


class ObjectsSerializer:
    def __init__(self, compiled_objects_read_path: Path):
        self.objects = read_yaml_to_dict(compiled_objects_read_path)

    def run(self) -> dict:
        """Runs the object serializer, serializing all objects. Does the following:
           1. Serialize all objects
           2. Link the dependsOn field of objects to other objects

        Returns:
            dict: A dictionary of object_name -> object mapping
        """
        object_map = {}
        for object_name, object_body in self.objects.items():
            object_map[object_name] = self.serialize_object(object_name, object_body)

    def serialize_object(self, object_name: str, object_body: dict) -> Object:
        """Serialize the object
           1. Serialize all the fields first
           2. Now serialize the rest of the object

        Args:
            object_name (str): Object name
            object_body (dict): Object description

        Returns:
            Object: The object
        """
        breakpoint()

    def serialize_fields(self, field: dict) -> Field:
        """Recursively (if it has an oftype) serialize a single field

        Args:
            field (dict): The field of the object

        Returns:
            Field: The field
        """
