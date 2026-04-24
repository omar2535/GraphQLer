"""DOSResourceExhaustionMaterializer: generates a query or mutation where all integer-like inputs
that commonly control result-set size (first, last, limit, count, size, offset, page, perPage, take)
are set to a very large value.  This tests whether the server enforces pagination limits before
fetching and returning a potentially unbounded dataset.
"""

from ..materializer import Materializer
from ..getter import Getter
from ..utils.materialization_utils import prettify_graphql_payload
from graphqler.utils.api import API
from graphqler.utils.objects_bucket import ObjectsBucket

LARGE_PAGINATION_VALUE = 999999

# Input names that are commonly used to control the size of a result set
PAGINATION_INPUT_NAMES = {
    "first", "last", "limit", "count", "size", "offset",
    "page", "perpage", "per_page", "take", "skip", "top",
}


class ResourceExhaustionGetter(Getter):
    """Overrides integer generation for pagination-like inputs to inject a very large value."""

    def get_random_int(self, input_name: str) -> int:
        if input_name.lower() in PAGINATION_INPUT_NAMES:
            return LARGE_PAGINATION_VALUE
        return super().get_random_int(input_name)


class DOSResourceExhaustionMaterializer(Materializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 20):
        super().__init__(api, fail_on_hard_dependency_not_met, getter=ResourceExhaustionGetter())
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        self.max_depth = max_depth

    def get_payload(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str = "") -> tuple[str, dict]:
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
        payload = f"query {{\n  {query_name} {inputs_str}\n  {query_output}\n}}"
        return prettify_graphql_payload(payload), self.used_objects

    def _get_mutation_payload(self, mutation_name: str, objects_bucket: ObjectsBucket) -> tuple[str, dict]:
        mutation_info = self.api.mutations[mutation_name]
        mutation_inputs = self.materialize_inputs(mutation_info, mutation_info["inputs"], objects_bucket, max_depth=self.max_depth)
        mutation_output = self.materialize_output(mutation_info, mutation_info["output"], objects_bucket, max_depth=self.max_depth)

        if mutation_inputs.strip():
            payload = f"mutation {{\n  {mutation_name}({mutation_inputs})\n  {mutation_output}\n}}"
        else:
            payload = f"mutation {{\n  {mutation_name}\n  {mutation_output}\n}}"
        return prettify_graphql_payload(payload), self.used_objects
