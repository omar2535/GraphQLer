"""Simple singleton class to parse mutation listings from the introspection query"""

from .parser import Parser


class MutationListParser(Parser):
    def __init__(self):
        pass

    def parse(self, introspection_data: dict) -> dict:
        """Parses the introspection data for only objects

        Args:
            data (dict): Introspection JSON as a dictionary

        Returns:
            dict: List of objects with their types
        """
        # Grab just the objects from the dict
        schema_types = introspection_data.get("data", {}).get("__schema", {}).get("types", [])
        mutation_object = [t for t in schema_types if t.get("kind") == "OBJECT" and (t.get("name") == "Mutation" or t.get("name") == "Mutations")]

        # If no mutations, just early return
        if len(mutation_object) == 0:
            return {}
        mutations = mutation_object[0]["fields"]

        # Convert it to the YAML structure we want
        mutation_info_dict = {}
        for mutation in mutations:
            mutation_name = mutation["name"]
            mutation_args = self.extract_arg_info(mutation["args"])
            is_deprecated = mutation["isDeprecated"]
            description = mutation["description"]

            return_type = {"kind": mutation["type"]["kind"], "name": mutation["type"]["name"], "ofType": self.extract_oftype(mutation["type"]), "type": mutation["type"]["name"]}

            mutation_info_dict[mutation_name] = {"name": mutation_name, "inputs": mutation_args, "output": return_type, "isDepracated": is_deprecated, "description": description}

        return mutation_info_dict
