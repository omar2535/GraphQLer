"""Regular query materializer:
Materializes a query that is ready to be sent off
"""

from .regular_materializer import RegularMaterializer
from .query_materializer import QueryMaterializer
from .utils import prettify_graphql_payload
from graphqler.constants import MAX_OUTPUT_SELECTOR_DEPTH, MAX_INPUT_DEPTH
import logging


class RegularQueryMaterializer(QueryMaterializer, RegularMaterializer):
    def __init__(self, objects: dict, queries: dict, input_objects: dict, enums: dict, fail_on_hard_dependency_not_met: bool = True):
        super().__init__(objects, queries, input_objects, enums)
        self.objects = objects
        self.queries = queries
        self.input_objects = input_objects
        self.enums = enums
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met

    def get_payload(self, query_name: str, objects_bucket: dict) -> tuple[str, dict]:
        """Materializes the query with parameters filled in
           1. Make sure all dependencies are satisfied (hardDependsOn)
           2. Fill in the inputs ()

        Args:
            query_name (str): The query name
            objects_bucket (dict): The bucket of objects that have already been created

        Returns:
            tuple[str, dict]: The string of the query, and the used objects list
        """
        self.used_objects = {}  # Reset the used_objects list per run (from parent class)
        query_info = self.queries[query_name]
        query_inputs = self.materialize_inputs(query_info, query_info["inputs"], objects_bucket, max_depth=MAX_INPUT_DEPTH)
        query_outputs = self.materialize_output(query_info["output"], [], False, max_depth=MAX_OUTPUT_SELECTOR_DEPTH)

        if query_inputs != "":
            query_inputs = f"({query_inputs})"

        payload = f"""
        query {{
            {query_name} {query_inputs}
            {query_outputs}
        }}
        """
        pretty_payload = prettify_graphql_payload(payload)
        return pretty_payload, self.used_objects
