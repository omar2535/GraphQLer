
"""Regular mutation materializer:
Materializes a mutation that is ready to be sent off
"""

from .materializer import Materializer
from .utils.materialization_utils import prettify_graphql_payload
from .getter import Getter
from graphqler.config import MAX_OUTPUT_SELECTOR_DEPTH, MAX_INPUT_DEPTH
from graphqler.utils.api import API
from graphqler.utils.objects_bucket import ObjectsBucket


class MaximalPayloadMaterializer(Materializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = True):
        self.getters = Getter()
        self.api = api
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        super().__init__(self.api, self.fail_on_hard_dependency_not_met, max_depth=MAX_OUTPUT_SELECTOR_DEPTH, getter=self.getters)

    def get_payload(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str) -> tuple[str, dict]:
        """Materializes the mutation with parameters filled in
           1. Make sure all dependencies are satisfied (hardDependsOn)
           2. Fill in the inputs ()

        Args:
            name (str): The name of either the mutation or query
            objects_bucket (dict): The bucket of objects that have already been created
            graphql_type (str): The type of the graphql operation (Query or Mutation)

        Returns:
            tuple[str, dict]: The string of the payload, and the used objects list
        """
        self.used_objects = {}  # Reset the used_objects list per run (from parent class)
        if graphql_type == "Query":
            return self._get_query_payload(name,
                                           objects_bucket,
                                           max_input_depth=MAX_INPUT_DEPTH,
                                           max_output_depth=MAX_OUTPUT_SELECTOR_DEPTH,
                                           minimal_materialization=False)
        elif graphql_type == "Mutation":
            return self._get_mutation_payload(name,
                                              objects_bucket,
                                              max_input_depth=MAX_INPUT_DEPTH,
                                              max_output_depth=MAX_OUTPUT_SELECTOR_DEPTH,
                                              minimal_materialization=False)
        else:
            raise ValueError("Invalid graphql_type provided")

    def _get_query_payload(self,
                           query_name: str,
                           objects_bucket: ObjectsBucket,
                           max_input_depth: int = MAX_INPUT_DEPTH,
                           max_output_depth: int = MAX_OUTPUT_SELECTOR_DEPTH,
                           minimal_materialization: bool = False) -> tuple[str, dict]:
        query_info = self.api.queries[query_name]
        query_inputs = self.materialize_inputs(query_info, query_info["inputs"], objects_bucket, max_depth=max_input_depth)
        query_output = self.materialize_output(query_info, query_info["output"], objects_bucket, max_depth=max_output_depth, minimal_materialization=minimal_materialization)

        if query_inputs != "":
            query_inputs = f"({query_inputs})"

        payload = f"""
        query {{
            {query_name} {query_inputs}
            {query_output}
        }}
        """
        pretty_payload = prettify_graphql_payload(payload)
        return pretty_payload, self.used_objects

    def _get_mutation_payload(self,
                              mutation_name: str,
                              objects_bucket: ObjectsBucket,
                              max_input_depth: int = MAX_INPUT_DEPTH,
                              max_output_depth: int = MAX_OUTPUT_SELECTOR_DEPTH,
                              minimal_materialization: bool = False) -> tuple[str, dict]:
        mutation_info = self.api.mutations[mutation_name]
        mutation_inputs = self.materialize_inputs(mutation_info, mutation_info["inputs"], objects_bucket, max_depth=max_input_depth)
        mutation_output = self.materialize_output(mutation_info, mutation_info["output"], objects_bucket, max_depth=max_output_depth, minimal_materialization=minimal_materialization)

        if mutation_inputs.strip() == "":
            mutation_payload = f"""
            mutation {{
                {mutation_name}
                {mutation_output}
            }}
            """
        else:
            mutation_payload = f"""
            mutation {{
                {mutation_name} (
                    {mutation_inputs}
                )
                {mutation_output}
            }}
            """
        pretty_payload = prettify_graphql_payload(mutation_payload)
        return pretty_payload, self.used_objects
