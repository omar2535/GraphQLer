"""
This will resolve the inputs of a mutation to object. A few fields will be introduced to a mutation, namely:
mutationType: One of [CREATE,UPDATE,DELETE,UNKNOWN] - this is determined semantically
hardDependsOn: A dictionary of inputname-object name that is required
               in the input (NON-NULL), depends on, ie: {'userId': 'User'}
softDependsOn: A dictionary of inputname-object name, depends on, ie: {'userId': 'User'}
"""

from typing import List

import pprint
import re


class MutationObjectResolver:
    def __init__(self):
        pass

    def resolve(
        self,
        objects: dict,
        mutations: dict,
        input_objects: dict,
    ) -> dict:
        """Resolve mutation inputs to queries based on semantical understanding of IDs and adds the mutation type
            one of [CREATE, UPDATE, DELETE, UNKNOWN]

        Args:
            objects (dict): Objects to link the mutations to
            mutations (dict): Mutations to parse through
            input_objects (dict): Input objects to recursively search through different input object inputs

        Returns:
            dict: The mutations enriched with aforementioned fields
        """
        for mutation_name, mutation in mutations.items():
            mutation_type = self.get_mutation_type(mutation_name)
            inputs_related_to_ids = self.get_inputs_related_to_ids(mutation["inputs"], input_objects)
            resolved_objects_to_inputs = self.resolve_inputs_related_to_ids_to_objects(inputs_related_to_ids, objects)

            # Assign the enrichments
            mutations[mutation_name]["hardDependsOn"] = resolved_objects_to_inputs["hardDependsOn"]
            mutations[mutation_name]["softDependsOn"] = resolved_objects_to_inputs["softDependsOn"]
            mutations[mutation_name]["mutationType"] = mutation_type

        return mutations

    def get_mutation_type(self, mutation_name: str) -> str:
        """Gets the method type as a string

        Args:
            mutation_name (str): The mutation name

        Returns:
            str: One of [CREATE,UDPATE,DELETE,UNKNOWN]
        """
        create_pattern = re.compile(r"^(create|add|insert)", re.IGNORECASE)
        update_pattern = re.compile(r"^(update|modify|edit)", re.IGNORECASE)
        delete_pattern = re.compile(r"^(delete|remove|erase)", re.IGNORECASE)

        # Check if the method name matches any pattern
        if create_pattern.match(mutation_name):
            return "CREATE"
        elif update_pattern.match(mutation_name):
            return "UPDATE"
        elif delete_pattern.match(mutation_name):
            return "DELETE"
        else:
            return "UNKNOWN"

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

    def resolve_inputs_related_to_ids_to_objects(self, inputs_related_to_ids: dict, objects: dict) -> dict:
        """Resolves inputs related to IDs by looking at the name of the parameter after the ID string is removed

        Args:
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
                pass
            elif input_name.lower() == "ids":
                pass
            elif input_name[-2:].lower() == "id":
                object_name = object_name[:-2]
            elif input_name[-3:].lower() == "ids":
                object_name = object_name[:-3]
            guessed_object_name = object_name[0].upper() + object_name[1:]

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
        return input["ofType"] and input["ofType"]["kind"] == "SCALAR" and input["ofType"]["name"] == "ID"
