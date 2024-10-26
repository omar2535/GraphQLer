"""
This will resolve the inputs of a mutation to object. A few fields will be introduced to a mutation, namely:
mutationType: One of [CREATE,UPDATE,DELETE,UNKNOWN] - this is determined semantically
hardDependsOn: A dictionary of inputname-object name that is required
               in the input (NON-NULL), depends on, ie: {'userId': 'User'}
softDependsOn: A dictionary of inputname-object name, depends on, ie: {'userId': 'User'}
"""

import re

from .resolver import Resolver


class MutationObjectResolver(Resolver):
    def __init__(self):
        super().__init__()

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
            mutation_type = self.get_mutation_action(mutation_name, mutation["description"])
            inputs_related_to_ids = self.get_inputs_related_to_ids(mutation["inputs"], input_objects)
            resolved_objects_to_inputs = self.resolve_inputs_related_to_ids_to_objects(mutation_name, inputs_related_to_ids, objects)

            # Assign the enrichments
            mutations[mutation_name]["hardDependsOn"] = resolved_objects_to_inputs["hardDependsOn"]
            mutations[mutation_name]["softDependsOn"] = resolved_objects_to_inputs["softDependsOn"]
            mutations[mutation_name]["mutationType"] = mutation_type

        return mutations

    def get_mutation_action(self, mutation_name: str, mutation_description: str | None) -> str:
        """Gets the method action as a string by checking both the method name and method description

        Args:
            mutation_name (str): The mutation name
            mutation_description (str | None): The mutation description

        Returns:
            str: One of [CREATE,UDPATE,DELETE,UNKNOWN]
        """
        create_pattern = re.compile(r"(create|add|insert)", re.IGNORECASE)
        update_pattern = re.compile(r"(update|modify|edit)", re.IGNORECASE)
        delete_pattern = re.compile(r"(delete|remove|erase)", re.IGNORECASE)

        # Check if the method name matches any pattern
        if create_pattern.search(mutation_name):
            return "CREATE"
        elif update_pattern.search(mutation_name):
            return "UPDATE"
        elif delete_pattern.search(mutation_name):
            return "DELETE"

        # Check if the method description matches any pattern
        if mutation_description:
            if create_pattern.search(mutation_description):
                return "CREATE"
            elif update_pattern.search(mutation_description):
                return "UPDATE"
            elif delete_pattern.search(mutation_description):
                return "DELETE"

        return "UNKNOWN"
