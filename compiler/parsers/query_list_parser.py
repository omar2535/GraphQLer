"""Simple singleton class to parse object listings from the introspection query"""
from typing import List


class QueryListParser:
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

    def __extract_arg_info(self, field):
        input_args = {}
        for arg in field:
            arg_info = {
                "name": arg["name"],
                "type": arg["type"]["name"] if "name" in arg["type"] else None,
                "ofType": self.__extract_oftype(arg),
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
        queries_object = [t for t in schema_types if t.get("kind") == "OBJECT" and t.get("name") == "Query"]
        queries = queries_object[0]["fields"]

        # Convert it to the YAML structure we want
        query_info_dict = {}
        for query in queries:
            query_name = query["name"]
            query_args = self.__extract_arg_info(query["args"])
            return_type = {
                "kind": query["type"]["kind"],
                "name": query["type"]["name"],
                "ofType": self.__extract_oftype(query),
            }

            query_info_dict[query_name] = {
                "name": query_name,
                "inputs": query_args,
                "outputs": return_type,
            }

        return query_info_dict
