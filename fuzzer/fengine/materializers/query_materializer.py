"""Materializer
Base class for a query materializer
"""


class QueryMaterializer:
    def __init__(self, objects: dict, queries: dict, input_objects: dict, enums: dict):
        super().__init__(objects, queries, input_objects, enums)
        self.objects = objects
        self.queries = queries
        self.input_objects = input_objects
        self.enums = enums

    def get_payload(self, query_name: str, objects_bucket: dict) -> tuple[str, dict]:
        pass
