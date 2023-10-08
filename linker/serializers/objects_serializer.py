"""
Object serializer: serialize all compiled objects into a dictionary of object_name -> object pair
"""

from pathlib import Path
from utils.file_utils import read_yaml_to_dict
from graphqler_types import Object


class ObjectsSerializer:
    def __init__(self, compiled_objects_read_path: Path):
        self.objects = read_yaml_to_dict(compiled_objects_read_path)

    def run(self):
        object_map = {}
        for object_name, object_body in self.objects.items():
            object_map[object_name] = self.serialize_object(object_body)

    def serialize_object(self, object_body: dict) -> Object:
        pass
