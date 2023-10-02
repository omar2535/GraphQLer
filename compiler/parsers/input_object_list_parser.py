"""
Parser for input objects
Input objects can depend on other input objects https://spec.graphql.org/June2018/#sec-Input-Object
"""
from typing import List
from .parser import Parser


class InputObjectListParser(Parser):
    def __init__(self):
        pass

    def __extract_field_info(self, field):
        field_info = {
            "name": field["name"],
            "kind": field["type"]["kind"],
            "type": field["type"]["name"] if "name" in field["type"] else None,
            "ofType": self.extract_oftype(field)
            if field["type"]["ofType"] and field["type"]["ofType"]["name"]
            else None,
        }
        return field_info

    def parse(self, introspection_data: dict) -> List[dict]:
        """Parses the introspection data for only objects

        Args:
            data (dict): Introspection JSON as a dictionary

        Returns:
            List[dict]: List of objects with their types
        """
        # Grab just the objects from the dict
        schema_types = introspection_data.get("data", {}).get("__schema", {}).get("types", [])
        object_types = [t for t in schema_types if t.get("kind") == "INPUT_OBJECT"]

        # Convert it to the YAML structure we want
        input_object_info_dict = {}
        for obj in object_types:
            object_name = obj["name"]
            input_object_info_dict[object_name] = {
                "kind": obj["kind"],
                "name": object_name,
                "inputFields": [self.__extract_field_info(field) for field in obj["inputFields"]],
            }

        return input_object_info_dict
