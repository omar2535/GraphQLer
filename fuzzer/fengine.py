"""FEngine: Responsible for getting the materialized query, running it against the API, and returning if it succeeds
            and the new objects that were returned (if any were updated)
"""

from .materializers import RegularMutationMaterializer


class FEngine:
    def __init__(self, queries: dict, objects: dict, mutations: dict, input_objects: dict, enums: dict, url: str):
        """The intiialization of the FEnginer

        Args:
            queries (dict): The possible queries
            objects (dict): The possible objects
            mutations (dict): The possible mutations
            input_objects (dict): The possible input_objects
            enums (dict): The possible enums
            url (str): The string of the URL
        """
        self.queries = queries
        self.objects = objects
        self.mutations = mutations
        self.input_objects = input_objects
        self.enums = enums
        self.url = url

    def run_regular_mutation(self, mutation_name: str, objects_bucket: dict) -> tuple[dict, bool]:
        """Runs the mutation, and returns a new objects bucket. Performs a few things:
           1. Materializes the mutation with its parameters (resolving any dependencies from the object_bucket)
           2. Send the mutation against the server and gets the parses the object from the response
           3. Saves the result in the objects_bucket

        Args:
            mutation_name (str): Name of the mutation
            objects_bucket (dict): The current objects bucket

        Returns:
            tuple[dict, bool]: The new objects bucket, and whether the mutation succeeded or not
        """
        # Step 1
        materializer = RegularMutationMaterializer(self.objects, self.mutations, self.input_objects, self.enums)
        materializer.get_payload(mutation_name, objects_bucket)

        # Step 2
        pass

        # Step 3
        pass

        # Stub - TODO: Change this
        return (objects_bucket, True)

    def run_regular_query(self, name: str, objects_bucket: dict) -> tuple[dict, bool]:
        """Runs the query, and returns a new objects bucket

        Args:
            name (str): The name of the query
            objects_bucket (dict): The objects bucket

        Returns:
            tuple[dict, bool]: The new objects bucket, and whether the mutation succeeded or not
        """
        return (objects_bucket, True)
