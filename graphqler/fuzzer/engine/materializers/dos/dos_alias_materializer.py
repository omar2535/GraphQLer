"""DOSAliasMaterializer: Generates a payload that uses field aliases to invoke the same resolver many times
in a single GraphQL request. This tests whether the server protects against alias-based amplification attacks.
"""

from ..materializer import Materializer
from ..utils.materialization_utils import prettify_graphql_payload
from graphqler.utils.api import API
from graphqler.utils.objects_bucket import ObjectsBucket

ALIAS_REPEAT_COUNT = 10


class DOSAliasMaterializer(Materializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 5):
        super().__init__(api, fail_on_hard_dependency_not_met)
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        self.max_depth = max_depth

    def get_payload(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str = "") -> tuple[str, dict]:
        """Builds a single query/mutation containing ALIAS_REPEAT_COUNT aliased copies of the operation.

        Args:
            name (str): The query or mutation name
            objects_bucket (ObjectsBucket): The objects bucket
            graphql_type (str): "Query" or "Mutation"

        Returns:
            tuple[str, dict]: The payload string and used objects map
        """
        if graphql_type == "Query":
            return self._get_query_payload(name, objects_bucket)
        elif graphql_type == "Mutation":
            return self._get_mutation_payload(name, objects_bucket)
        else:
            raise ValueError("Invalid graphql_type provided")

    def _get_query_payload(self, query_name: str, objects_bucket: ObjectsBucket) -> tuple[str, dict]:
        query_info = self.api.queries[query_name]
        query_inputs = self.materialize_inputs(query_info, query_info["inputs"], objects_bucket, max_depth=self.max_depth)
        query_output = self.materialize_output(query_info, query_info["output"], objects_bucket, max_depth=self.max_depth)

        inputs_str = f"({query_inputs})" if query_inputs.strip() else ""

        aliases = "\n".join(
            f"alias{i}: {query_name} {inputs_str} {query_output}"
            for i in range(ALIAS_REPEAT_COUNT)
        )
        payload = f"query {{\n{aliases}\n}}"
        return prettify_graphql_payload(payload), self.used_objects

    def _get_mutation_payload(self, mutation_name: str, objects_bucket: ObjectsBucket) -> tuple[str, dict]:
        mutation_info = self.api.mutations[mutation_name]
        mutation_inputs = self.materialize_inputs(mutation_info, mutation_info["inputs"], objects_bucket, max_depth=self.max_depth)
        mutation_output = self.materialize_output(mutation_info, mutation_info["output"], objects_bucket, max_depth=self.max_depth)

        inputs_str = f"({mutation_inputs})" if mutation_inputs.strip() else ""

        aliases = "\n".join(
            f"alias{i}: {mutation_name} {inputs_str} {mutation_output}"
            for i in range(ALIAS_REPEAT_COUNT)
        )
        payload = f"mutation {{\n{aliases}\n}}"
        return prettify_graphql_payload(payload), self.used_objects
