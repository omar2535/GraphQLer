"""Regular mutation materializer:
Materializes a mutation that is ready to be sent off
"""


class RegularMutationMaterializer:
    def __init__(self, mutations: dict, input_objects: dict, enums: dict):
        self.mutations = mutations
        self.input_objects = input_objects
        self.enums = enums

    def materialize(self, mutation_name: str, objects_bucket: dict) -> str:
        """Materializes the mutation with parameters filled in

        Args:
            mutation_name (str): The mutation name
            objects_bucket (dict): The bucket of objects that have already been created

        Returns:
            str: The string of the mutation
        """
        pass
