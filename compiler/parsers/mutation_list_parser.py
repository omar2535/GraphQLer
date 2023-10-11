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
                "kind": arg["type"]["kind"] if "kind" in arg["type"] else None,
                "ofType": self.extract_oftype(arg["type"]),
                "defaultValue": arg["defaultValue"],
            }
            input_args[arg["name"]] = arg_info
        return input_args

    def parse(self, introspection_data: dict) -> dict:
        """Parses the introspection data for only objects

        Args:
            data (dict): Introspection JSON as a dictionary

        Returns:
            dict: List of objects with their types
        """
        # Grab just the objects from the dict
        schema_types = introspection_data.get("data", {}).get("__schema", {}).get("types", [])
        mutation_object = [t for t in schema_types if t.get("kind") == "OBJECT" and t.get("name") == "Mutation"]

        # If no mutations, just early return
        if len(mutation_object) == 0:
            return {}
        mutations = mutation_object[0]["fields"]

        # Convert it to the YAML structure we want
        mutation_info_dict = {}
        for mutation in mutations:
            mutation_name = mutation["name"]
            mutation_args = self.__extract_arg_info(mutation["args"])
            is_deprecated = mutation["isDeprecated"]

            return_type = {"kind": mutation["type"]["kind"], "name": mutation["type"]["name"], "ofType": self.extract_oftype(mutation["type"]), "type": mutation["type"]["name"]}

            mutation_info_dict[mutation_name] = {
                "name": mutation_name,
                "inputs": mutation_args,
                "output": return_type,
                "isDepracated": is_deprecated,
            }

        return mutation_info_dict
