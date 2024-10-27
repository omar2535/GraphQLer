"""
Enum objects: https://spec.graphql.org/June2018/#sec-Enum
"""

from .parser import Parser
from typing import List


class EnumListParser(Parser):
    def __init__(self):
        self.excluded_types = [
            "Mutation",
            "Query",
            "__Schema",
            "__Type",
            "__TypeKind",
            "__Field",
            "__InputValue",
            "__EnumValue",
            "__Directive",
            "__DirectiveLocation",
        ]

    def extract_enum_values(self, enum_values: List[dict]) -> List[dict]:
        """Extract only the relavent fields from the possible enumeration values

        Args:
            enum_values (List[dict]): List of possible values of the ENUM object

        Returns:
            List[dict]: List of possible balues of the ENUM object but filtered for only relavent fields
        """
        list_of_enum_values = []
        for enum_value in enum_values:
            filtered_enum_value = {"name": enum_value["name"], "isDeprecated": enum_value["isDeprecated"]}
            list_of_enum_values.append(filtered_enum_value)
        return list_of_enum_values

    def parse(self, introspection_data: dict) -> dict:
        """Parses the introspection data for only objects

        Args:
            data (dict): Introspection JSON as a dictionary

        Returns:
            dict: List of objects with their types
        """
        # Grab just the objects from the dict
        schema_types = introspection_data.get("data", {}).get("__schema", {}).get("types", [])
        enum_objects = [t for t in schema_types if t.get("kind") == "ENUM" and t.get("name") not in self.excluded_types]

        built_enum_objects = {}
        for enum_object in enum_objects:
            enum_name = enum_object["name"]
            built_enum_objects[enum_name] = {"enumValues": self.extract_enum_values(enum_object["enumValues"])}
        return built_enum_objects
