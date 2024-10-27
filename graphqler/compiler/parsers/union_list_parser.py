"""
Union objects: https://spec.graphql.org/October2021/#sec-Unions
"""

from .parser import Parser
from typing import List


class UnionListParser(Parser):
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

    def extract_union_values(self, union_values: List[dict]) -> List[dict]:
        """Extract only the relavent fields from the possible union values

        Args:
            union_valies (List[dict]): List of possible values of the UNION object

        Returns:
            List[dict]: List of possible balues of the UNION object but filtered for only relavent fields.
                        We also add the type field to the object if the kind if an object
        """
        list_of_union_values = []
        for union_value in union_values:
            filtered_union_value = {
                "kind": union_value["kind"],
                "name": union_value["name"],
                "ofType": union_value["ofType"],
                "type": union_value["name"] if union_value["kind"] == "OBJECT" else None,
            }
            list_of_union_values.append(filtered_union_value)
        return list_of_union_values

    def parse(self, introspection_data: dict) -> dict:
        """Parses the introspection data for only objects

        Args:
            data (dict): Introspection JSON as a dictionary

        Returns:
            dict: List of objects with their types
        """
        # Grab just the objects from the dict
        schema_types = introspection_data.get("data", {}).get("__schema", {}).get("types", [])
        union_objects = [t for t in schema_types if t.get("kind") == "UNION" and t.get("name") not in self.excluded_types]

        built_union_objects = {}
        for union_object in union_objects:
            union_name = union_object["name"]
            built_union_objects[union_name] = {"possibleTypes": self.extract_union_values(union_object["possibleTypes"])}
        return built_union_objects
