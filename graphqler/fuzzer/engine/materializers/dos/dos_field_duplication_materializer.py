"""DOSFieldDuplicationMaterializer: generates a payload where a single scalar field is repeated many
times (via aliases) inside the selection set of a query or mutation.  This tests whether the server
deduplicates or limits redundant field resolutions before they reach the resolver layer.
"""

from ..materializer import Materializer
from ..utils.materialization_utils import prettify_graphql_payload
from graphqler.utils.api import API
from graphqler.utils.objects_bucket import ObjectsBucket
from graphqler.utils.parser_utils import get_base_oftype, is_simple_scalar

FIELD_DUPLICATION_COUNT = 100


class DOSFieldDuplicationMaterializer(Materializer):
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

    def _first_scalar_field_name(self, output: dict) -> str | None:
        """Walk through NON_NULL/LIST wrappers to the base OBJECT type and return
        the name of its first scalar field, or None if there is none."""
        base = get_base_oftype(output)
        if base.get("kind") != "OBJECT":
            return None
        type_name = base.get("type")
        if not type_name or type_name not in self.api.objects:
            return None
        for field in self.api.objects[type_name].get("fields", []):
            if is_simple_scalar(field):
                return field["name"]
        return None

    def _build_duplicated_selection(self, output: dict) -> str:
        """Return a GraphQL selection set string with one scalar repeated 100 times via aliases.
        Returns an empty string when no suitable scalar field can be found."""
        scalar_name = self._first_scalar_field_name(output)
        if not scalar_name:
            return ""
        aliases = "\n".join(f"  f{i}: {scalar_name}" for i in range(FIELD_DUPLICATION_COUNT))
        return "{\n" + aliases + "\n}"

    # ------------------------------------------------------------------
    # Payload builders
    # ------------------------------------------------------------------

    def _get_query_payload(self, query_name: str, objects_bucket: ObjectsBucket) -> tuple[str, dict]:
        query_info = self.api.queries[query_name]
        query_inputs = self.materialize_inputs(query_info, query_info["inputs"], objects_bucket, max_depth=self.max_depth)
        selection = self._build_duplicated_selection(query_info["output"])
        if not selection:
            selection = self.materialize_output(query_info, query_info["output"], objects_bucket, max_depth=self.max_depth)

        inputs_str = f"({query_inputs})" if query_inputs.strip() else ""
        payload = f"query {{\n  {query_name} {inputs_str} {selection}\n}}"
        return prettify_graphql_payload(payload), self.used_objects

    def _get_mutation_payload(self, mutation_name: str, objects_bucket: ObjectsBucket) -> tuple[str, dict]:
        mutation_info = self.api.mutations[mutation_name]
        mutation_inputs = self.materialize_inputs(mutation_info, mutation_info["inputs"], objects_bucket, max_depth=self.max_depth)
        selection = self._build_duplicated_selection(mutation_info["output"])
        if not selection:
            selection = self.materialize_output(mutation_info, mutation_info["output"], objects_bucket, max_depth=self.max_depth)

        if mutation_inputs.strip():
            payload = f"mutation {{\n  {mutation_name}({mutation_inputs}) {selection}\n}}"
        else:
            payload = f"mutation {{\n  {mutation_name} {selection}\n}}"
        return prettify_graphql_payload(payload), self.used_objects
