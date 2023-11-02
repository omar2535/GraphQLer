"""
This will resolve the inputs of a query to object. A few fields will be introduced to a query, namely:
hardDependsOn: A dictionary of inputname-object name that is required
               in the input (NON-NULL), depends on, ie: {'userId': 'User'}
softDependsOn: A dictionary of inputname-object name, depends on, ie: {'userId': 'User'}
"""

from utils.parser_utils import get_base_oftype
from .utils import find_closest_string


class QueryObjectResolver:
    def __init__(self):
        pass

    def resolve(
        self,
        objects: dict,
        queries: dict,
        input_objects: dict,
    ) -> dict:
        """Resolve query inputs to queries based on semantical understanding of IDs

        Args:
            objects (dict): Objects to link the mutations to
            queries (dict): Queries to parse through
            input_objects (dict): Input objects to recursively search through different input object inputs

        Returns:
            dict: The mutations enriched with aforementioned fields
        """
        for query_name, query in queries.items():
            inputs_related_to_ids = self.get_inputs_related_to_ids(query["inputs"], input_objects)
            resolved_objects_to_inputs = self.resolve_inputs_related_to_ids_to_objects(query_name, inputs_related_to_ids, objects)

            # Assign the enrichments
            queries[query_name]["hardDependsOn"] = resolved_objects_to_inputs["hardDependsOn"]
            queries[query_name]["softDependsOn"] = resolved_objects_to_inputs["softDependsOn"]

        return queries

    def get_inputs_related_to_ids(self, inputs: dict, input_objects: dict) -> dict:
        """Recursively finds any inputs that has ID in its name as that would imply it references other objects

        Args:
            inputs (dict): An inputs
            input_objects (dict): The input objects to be used for recursive search

        Returns:
            dict: A dictionary of id and if it's NON_NULL or not IE. {'userId': False, 'clientId': True}
        """
        if inputs is None:
            return {}
        else:
            found_ids = {}
            for input_name, input in inputs.items():
                if self.is_input_an_id(input):
                    found_ids[input_name] = input["kind"] == "NON_NULL"
                elif self.is_input_object(input):
                    input_object_name = input["ofType"]["name"]
                    input_object = input_objects[input_object_name]
                    found_ids.update(self.get_inputs_related_to_ids(input_object["inputFields"], input_objects))
            return found_ids

    ### -------------------------------------------------------------------------------------- ###
    ### BELOW IS THE SAME CODE AS mutation_object_resolver.py, JUST DUPLICATED FOR READABILITY ###
    ### -------------------------------------------------------------------------------------- ###
    def resolve_inputs_related_to_ids_to_objects(self, query_name: str, inputs_related_to_ids: dict, objects: dict) -> dict:
        """Resolves inputs related to IDs by looking at the name of the parameter after the ID string is removed

        Args:
            query_name (str): The name of the query for these inputs
            inputs_related_to_ids (dict): The inputs name (IE: userId)
            objects (dict): All the possible objects for this API

        Returns:
            dict: Input parameters to the objects and the required / not required mappings
        """
        input_id_object_mapping = {"hardDependsOn": {}, "softDependsOn": {}}

        for input_name, required in inputs_related_to_ids.items():
            # Get the object's name
            object_name = input_name
            if input_name.lower() == "id":
                guessed_object_name = find_closest_string(objects.keys(), query_name)
            elif input_name.lower() == "ids":
                guessed_object_name = find_closest_string(objects.keys(), query_name)
            elif input_name[-2:].lower() == "id":
                object_name = object_name[:-2]
                guessed_object_name = find_closest_string(objects.keys(), object_name)
            elif input_name[-3:].lower() == "ids":
                object_name = object_name[:-3]
                guessed_object_name = find_closest_string(objects.keys(), object_name)
            else:
                guessed_object_name = ""

            # Check if the object's name is in the object listing
            if guessed_object_name in objects:
                assigned_dependency_name = guessed_object_name
            else:
                assigned_dependency_name = "UNKNOWN"

            # Now assign it either a hardDependsOn or softDependsOn
            if required:
                input_id_object_mapping["hardDependsOn"][input_name] = assigned_dependency_name
            else:
                input_id_object_mapping["softDependsOn"][input_name] = assigned_dependency_name
        return input_id_object_mapping

    def is_input_object(self, input: dict) -> bool:
        return input["ofType"] and input["ofType"]["kind"] == "INPUT_OBJECT"

    def is_input_an_id(self, input: dict) -> bool:
        if input["ofType"]:
            input = get_base_oftype(input["ofType"])

        return input["kind"] == "SCALAR" and input["type"] == "ID"
