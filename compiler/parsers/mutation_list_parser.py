"""Simple singleton class to parse mutation listings from the introspection query"""
from typing import List
from .parser import Parser


class MutationListParser(Parser):
    def __init__(self):
        pass

    def __extract_arg_info(self, field):
        input_args = {}
        for arg in field:
            arg_info = {
                "name": arg["name"],
                "type": arg["type"]["name"] if "name" in arg["type"] else None,
                "ofType": self.__extract_oftype(arg),
                "defaultValue": arg["defaultValue"],
            }
            input_args[arg["name"]] = arg_info
        return input_args

    def __extract_oftype(self, field: dict) -> dict:
        """Extract the ofType. Assume that the nested ofType will always be null

        Args:
            field (dict): Field to extract from

        Returns:
            dict: The ofType dict
        """
        ofType = field["type"]["ofType"]
        if ofType and ofType["name"]:
            return {"kind": ofType["kind"], "name": ofType["name"]}

    def parse(self, introspection_data: dict) -> List[dict]:
        """Parses the introspection data for only objects

        Args:
            data (dict): Introspection JSON as a dictionary

        Returns:
            List[dict]: List of objects with their types
        """
        # Grab just the objects from the dict
        schema_types = introspection_data.get("data", {}).get("__schema", {}).get("types", [])
        mutation_object = [t for t in schema_types if t.get("kind") == "OBJECT" and t.get("name") == "Mutation"]
        mutations = mutation_object[0]["fields"]

        # Convert it to the YAML structure we want
        mutation_info_dict = {}
        for mutation in mutations:
            mutation_name = mutation["name"]
            mutation_args = self.__extract_arg_info(mutation["args"])
            is_deprecated = mutation["isDeprecated"]

            return_type = {
                "kind": mutation["type"]["kind"],
                "name": mutation["type"]["name"],
                "ofType": self.__extract_oftype(mutation),
            }

            mutation_info_dict[mutation_name] = {
                "name": mutation_name,
                "inputs": mutation_args,
                "output": return_type,
                "isDepracated": is_deprecated,
            }

        return mutation_info_dict
