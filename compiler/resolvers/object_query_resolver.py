"""Related queries to objects based on output type. We only look at the output to determine if a query is related to an object"""


class ObjectQueryResolver:
    def __init__(self):
        pass

    def resolve(self, objects: dict, queries: dict) -> dict:
        """Resolves the objects by attaching the correlated queries that output this object

        Args:
            objects (dict): The objects available
            queries (dict): The queries available

        Returns:
            dict: The objects dict enriched with a queries key
        """

        # Grab all the objects -> query list
        # if object name is empty, just skip to the next object since it was a SCALAR or built_in_type and not an OBJECT
        object_query_mapping = {}
        for query_name, query_body in queries.items():
            object_name = self.get_query_output_object(query_body["output"])
            if object_name == "":
                continue
            elif object_name in object_query_mapping:
                object_query_mapping[object_name].append(query_name)
            else:
                object_query_mapping[object_name] = [query_name]

        # Enrich each object with its mapped queries
        for object_name in objects.keys():
            if object_name in object_query_mapping:
                objects[object_name]["associatedQueries"] = object_query_mapping[object_name]
            else:
                objects[object_name]["associatedQueries"] = []
        return objects

    def get_query_output_object(self, outputType: dict) -> str:
        """Gets the object as a string from the query output

        Args:
            query_body (dict): The query's body

        Returns:
            str: A string of the object, or empty if it's a simple scalar that doesn't map to any object
        """
        if outputType["kind"] == "OBJECT":
            return outputType["name"]
        elif outputType["kind"] == "NON_NULL" or outputType["kind"] == "LIST":
            return self.get_query_output_object(outputType["ofType"])
        else:
            return ""
