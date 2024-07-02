"""Related queries and mutations to objects based on output type.
We only look at the output to determine if a method is related to an object
"""


class ObjectMethodResolver:
    def __init__(self):
        pass

    def resolve(self, objects: dict, queries: dict, mutations: dict) -> dict:
        """Resolves the objects by attaching the correlated queries/mutations that output this object

        Args:
            objects (dict): The objects available
            queries (dict): The queries available
            mutations (dict): The mutations available

        Returns:
            dict: The objects dict enriched with a queries key
        """

        object_query_mapping = self.get_object_query_mapping(queries)
        object_mutation_mapping = self.get_object_mutation_mapping(mutations)

        # Enrich each object with its mapped queries
        for object_name in objects.keys():
            if object_name in object_query_mapping:
                objects[object_name]["associatedQueries"] = object_query_mapping[object_name]
            else:
                objects[object_name]["associatedQueries"] = []

            if object_name in object_mutation_mapping:
                objects[object_name]["associatedMutatations"] = object_mutation_mapping[object_name]
            else:
                objects[object_name]["associatedMutatations"] = []
        return objects

    def get_object_query_mapping(self, queries: dict) -> dict:
        """Grab all objects -> List[query]. Must have kind of 'OBJECT'

        Args:
            mutations (dict): The queries

        Returns:
            dict: A mapping of object_name -> List of queries associated to the object
        """
        object_query_mapping = {}
        for query_name, query_body in queries.items():
            object_name = self.get_output_object(query_body["output"])
            if object_name == "":
                continue
            elif object_name in object_query_mapping:
                object_query_mapping[object_name].append(query_name)
            else:
                object_query_mapping[object_name] = [query_name]
        return object_query_mapping

    def get_object_mutation_mapping(self, mutations: dict) -> dict:
        """Grab all objects -> List[mutation]. Must have kind of 'OBJECT'

        Args:
            mutations (dict): The mutations

        Returns:
            dict: A mapping of object_name -> List of mutations associated to the object
        """
        # Grab all objects -> mutation list
        # if object name is empty, just skip to next object like above
        object_mutation_mapping = {}
        for mutation_name, mutation_body in mutations.items():
            object_name = self.get_output_object(mutation_body["output"])
            if object_name == "":
                continue
            elif object_name in object_mutation_mapping:
                object_mutation_mapping[object_name].append(mutation_name)
            else:
                object_mutation_mapping[object_name] = [mutation_name]
        return object_mutation_mapping

    def get_output_object(self, outputType: dict) -> str:
        """Gets the object as a string from the method's output

        Args:
            outputType (dict): The 'output' key of the method

        Returns:
            str: A string of the object, or empty if it's a simple scalar that doesn't map to any object
        """
        if outputType["kind"] == "OBJECT":
            return outputType["name"]
        elif outputType["kind"] == "NON_NULL" or outputType["kind"] == "LIST":
            return self.get_output_object(outputType["ofType"])
        else:
            return ""
