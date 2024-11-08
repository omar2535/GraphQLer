from .materializer import Materializer
from .utils.materialization_utils import prettify_graphql_payload
from graphqler.utils.api import API
from graphqler.utils.objects_bucket import ObjectsBucket
from .getter import Getter

from typing import override


class InjectionMaterializer(Materializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 20, injection_getter: Getter = Getter()):
        super().__init__(api, fail_on_hard_dependency_not_met, max_depth, injection_getter)
        self.max_depth = max_depth
        self.getter = injection_getter
        self.api = api
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met

    @override
    def get_payload(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str = "", minimal_materialization: bool = False) -> tuple[str, dict]:
        """Materializes the payload with parameters filled in
           1. Make sure all dependencies are satisfied (hardDependsOn)
           2. Fill in the inputs ()

        Args:
            name (str): The payload name of the Query or Mutation
            objects_bucket (dict): The bucket of objects that have already been created
            graphql_type (str): The type of the graphql operation (Query or Mutation)
            minimal_materialization (bool): Whether to minimize the materialization

        Returns:
            tuple[str, dict]: The string of the payload, and the used objects list
        """
        if graphql_type == "Query":
            return self._get_query_payload(name, objects_bucket)
        elif graphql_type == "Mutation":
            return self._get_mutation_payload(name, objects_bucket)
        else:
            raise ValueError("Invalid graphql_type provided")

    def _get_mutation_payload(self, mutation_name: str, objects_bucket: ObjectsBucket) -> tuple[str, dict]:
        mutation_info = self.api.mutations[mutation_name]
        mutation_inputs = self.materialize_inputs(mutation_info, mutation_info["inputs"], objects_bucket, max_depth=self.max_depth)
        mutation_output = self.materialize_output(mutation_info, mutation_info["output"], objects_bucket, max_depth=self.max_depth)
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

    def _get_query_payload(self, query_name: str, objects_bucket: ObjectsBucket) -> tuple[str, dict]:
        query_info = self.api.queries[query_name]
        query_inputs = self.materialize_inputs(query_info, query_info["inputs"], objects_bucket, max_depth=self.max_depth)
        query_output = self.materialize_output(query_info, query_info["output"], objects_bucket, max_depth=self.max_depth)

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
