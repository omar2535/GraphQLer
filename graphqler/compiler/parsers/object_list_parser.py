"""Simple singleton class to parse object listings from the introspection query"""

from .parser import Parser


class ObjectListParser(Parser):
    def __init__(self):
        self.excluded_types = [
            "__Schema",
            "__Type",
            "__TypeKind",
            "__Field",
            "__InputValue",
            "__EnumValue",
            "__Directive",
            "__DirectiveLocation",
        ]

    def __extract_field_info(self, field):
        field_info = {
            "name": field["name"],
            "kind": field["type"]["kind"],
            "type": field["type"]["name"] if "name" in field["type"] else None,
            "inputs": self.extract_arg_info(field["args"]),
            "ofType": self.extract_oftype(field["type"]),
        }
        return field_info

    def parse(self, introspection_data: dict) -> dict:
        """Parses the introspection data for only objects

        Args:
            data (dict): Introspection JSON as a dictionary

        Returns:
            dict: List of objects with their types
        """
        # Grab just the objects from the dict
        schema_types = introspection_data.get("data", {}).get("__schema", {}).get("types", [])
        object_types = [t for t in schema_types if t.get("kind") == "OBJECT" and t.get("name") not in self.excluded_types]

        # Convert it to the YAML structure we want
        object_info_dict = {}
        for obj in object_types:
            object_name = obj["name"]
            object_info_dict[object_name] = {
                "kind": obj["kind"],
                "name": object_name,
                "fields": [self.__extract_field_info(field) for field in obj["fields"]],
            }

        return object_info_dict
