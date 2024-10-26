"""Simple parser abstract class"""


class Parser:
    def __init__(self):
        pass

    def parse(self, introspection_data: dict) -> dict:
        """Abtract parse method, should be overriden by children classes

        Args:
            introspection_result (dict): The introspection data

        Raises:
            Exception: Throws exception if this method isn't overriden by child class

        Returns:
            dict: The parse result
        """
        raise Exception("Should not call parse on base Parser class")

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
