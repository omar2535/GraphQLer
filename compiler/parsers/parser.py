"""Simple parser abstract class"""


class Parser:
    def __init__(self):
        pass

    def parse(self, introspection_result: dict) -> dict:
        """Abtract parse method, should be overriden by children classes

        Args:
            introspection_result (dict): The introspection data

        Raises:
            Exception: Throws exception if this method isn't overriden by child class

        Returns:
            dict: The parse result
        """
        raise Exception("Should not call parse on base Parser class")

    def extract_oftype(self, field: dict) -> dict:
        """Extract the ofType. Assume that the nested ofType will always be null

        Args:
            field (dict): Field to extract from

        Returns:
            dict: The ofType dict
        """
        ofType = field["type"]["ofType"]
        if ofType and ofType["name"]:
            return {"kind": ofType["kind"], "name": ofType["name"]}
