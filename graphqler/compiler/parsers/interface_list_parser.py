"""
Interface objects: https://spec.graphql.org/October2021/#sec-Interfaces
"""

from .parser import Parser
from typing import List


class InterfaceListParser(Parser):
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

    def __extract_field_info(self, field):
        field_info = {
            "name": field["name"],
            "kind": field["type"]["kind"],
            "type": field["type"]["name"] if "name" in field["type"] else None,
            "ofType": self.extract_oftype(field["type"]),
        }
        return field_info

    def extract_possible_types(self, possible_types: List[dict]) -> List[dict]:
        """Extract the possible types from the interface

        Args:
            possible_types (List[dict]): List of possible types of the INTERFACE object

        Returns:
            List[dict]: List of possible values of the interface object
        """
        possible_types_list = []
        for possible_type in possible_types:
            formatted_possible_type = {
                "kind": possible_type["kind"],
                "name": possible_type["name"],
                "ofType": possible_type["ofType"],
                "type": possible_type["name"] if possible_type["kind"] == "OBJECT" else None,
            }
            possible_types_list.append(formatted_possible_type)
        return possible_types_list

    def parse(self, introspection_data: dict) -> dict:
        """Parses the introspection data for only INTERFACE objects

        Args:
            data (dict): Introspection JSON as a dictionary

        Returns:
            dict: Dictionary of INTERFACE objects with their types
        """
        # Grab just the objects from the dict
        schema_types = introspection_data.get("data", {}).get("__schema", {}).get("types", [])
        interfaces = [t for t in schema_types if t.get("kind") == "INTERFACE" and t.get("name") not in self.excluded_types]

        interfaces_dict = {}
        for interface in interfaces:
            interface_name = interface["name"]
            interfaces_dict[interface_name] = {
                "kind": interface["kind"],
                "name": interface["name"],
                "fields": [self.__extract_field_info(field) for field in interface["fields"]],
                "possibleTypes": self.extract_possible_types(interface["possibleTypes"]),
            }

        return interfaces_dict
