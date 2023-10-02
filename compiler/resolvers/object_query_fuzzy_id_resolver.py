"""Class to run the fuzzy ID resolver to determine if an output ID correlates to an object
   based on its naming scheme"""


class ObjectQueryFuzzyIdResolver:
    def __init__(self):
        pass

    def parse(self):
        # TODO: Simple stub for now
        pass

    def parse_object_name_from_scalar_id_name(self, scalarName: str) -> str:
        """Tries to infer the object name that this ID is pointing to

        Args:
            scalarName (str): The scalar name (IE. userId)

        Returns:
            str: The object name (IE. User)
        """
        object_name = scalarName
        last_2_chars = scalarName[-2:]
        if last_2_chars.lower() == "id":
            object_name = object_name[:-2]
        return object_name[0].upper() + object_name[1:]

    def determine_if_id_scalar_output_and_get_name(self, type: dict) -> str:
        pass
