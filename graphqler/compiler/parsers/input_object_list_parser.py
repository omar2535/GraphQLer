"""
Parser for input objects
Input objects can depend on other input objects https://spec.graphql.org/June2018/#sec-Input-Object
"""

from .parser import Parser


class InputObjectListParser(Parser):
    def __init__(self):
        pass

    def __extract_field_info(self, input_fields):
        resulting_input_fields = {}
        for field in input_fields:
            field_name = field["name"]
            resulting_input_fields[field_name] = {
                "kind": field["type"]["kind"],
                "type": field["type"]["name"] if "name" in field["type"] else None,
                "ofType": self.extract_oftype(field["type"]),
                "name": field["type"]["name"] if "name" in field["type"] else None,
            }

        return resulting_input_fields

    def parse(self, introspection_data: dict) -> dict:
        """Parses the introspection data for only objects

        Args:
            data (dict): Introspection JSON as a dictionary

        Returns:
            dict: List of objects with their types
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
                "inputFields": self.__extract_field_info(obj["inputFields"]),
            }

        return input_object_info_dict
