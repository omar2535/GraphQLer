"""Simple parser abstract class"""

from abc import ABC, abstractmethod


class Parser(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def parse(self, introspection_data: dict) -> dict:
        """Parse the introspection data and return a structured dict.

        Args:
            introspection_data (dict): The full introspection JSON response.

        Returns:
            dict: Parsed result keyed by GraphQL type name.
        """
        ...

    def extract_oftype(self, field: dict) -> dict | None:
        """Extract the ofType. Assume that at the lowest level, nested ofType will always be null

        Args:
            field (dict): Field's "type" to extract from

        Returns:
            dict: The ofType dict
        """
        ofType = field["ofType"]
        if ofType:
            nested_ofType = self.extract_oftype(field["ofType"])
            return {"kind": ofType["kind"], "name": ofType["name"], "ofType": nested_ofType, "type": ofType["name"]}
        else:
            return None

    def extract_arg_info(self, args: list[dict]) -> dict:
        """Extracts the arg information from a field

        Args:
            field (dict): An array of arguments

        Returns:
            dict: A dictionary of the arguments
        """
        input_args = {}
        for arg in args:
            arg_info = {
                "name": arg["name"],
                "description": arg["description"],
                "type": arg["type"]["name"] if "name" in arg["type"] else None,
                "kind": arg["type"]["kind"] if "kind" in arg["type"] else None,
                "ofType": self.extract_oftype(arg["type"]),
                "defaultValue": arg["defaultValue"],
            }
            input_args[arg["name"]] = arg_info
        return input_args
