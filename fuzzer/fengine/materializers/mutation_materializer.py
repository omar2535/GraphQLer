"""Materializer
Base class for a mutation materializer
"""


class MutationMaterializer:
    def __init__(self, objects: dict, mutations: dict, input_objects: dict, enums: dict):
        super().__init__(objects, mutations, input_objects, enums)
        self.objects = objects
        self.mutations = mutations
        self.input_objects = input_objects
        self.enums = enums

    def get_payload(self, mutation_name: str, objects_bucket: dict) -> tuple[str, dict]:
        pass
