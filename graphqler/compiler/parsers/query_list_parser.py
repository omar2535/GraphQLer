"""Simple singleton class to parse query listings from the introspection query"""

from .parser import Parser


class QueryListParser(Parser):
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
        query_type_name = introspection_data.get("data", {}).get("__schema", {}).get("queryType", {}).get("name", "Query")
        queries_object = [t for t in schema_types if t.get("kind") == "OBJECT" and t.get("name") == query_type_name]

        # No queries in the introspection
        if len(queries_object) == 0:
            return {}

        queries = queries_object[0]["fields"]

        # Convert it to the YAML structure we want
        query_info_dict = {}
        for query in queries:
            query_name = query["name"]
            query_args = self.__extract_arg_info(query["args"])
            return_type = {"kind": query["type"]["kind"], "name": query["type"]["name"], "ofType": self.extract_oftype(query["type"]), "type": query["type"]["name"]}

            query_info_dict[query_name] = {
                "name": query_name,
                "inputs": query_args,
                "output": return_type,
            }

        return query_info_dict
