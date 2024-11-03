from graphqler.fuzzer.engine.materializers.materializer import Materializer
from graphqler.fuzzer.engine.materializers.getter import Getter
from graphqler.fuzzer.engine.materializers.utils.materialization_utils import prettify_graphql_payload
from graphqler.utils.api import API
from graphqler.utils.objects_bucket import ObjectsBucket

import random
from typing import override


class FieldSuggestionMaterializer(Materializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 20, injection_getter: Getter = Getter()):
        super().__init__(api, fail_on_hard_dependency_not_met, max_depth, injection_getter)
        self.max_depth = max_depth
        self.getter = injection_getter
        self.api = api
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met

    @override
    def get_payload(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str = "") -> tuple[str, dict]:
        """Materializes a query that has a field suggestion

        Args:
            name (str): The payload name of the Query or Mutation
            objects_bucket (dict): The bucket of objects that have already been created
            graphql_type (str): The type of the graphql operation (Query or Mutation)

        Returns:
            tuple[str, dict]: The string of the payload, and the used objects list
        """
        random_query_name = random.choice(list(self.api.queries.keys()))
        random_query_name_mispelt = random_query_name + "abc"
        payload = f"""
            query {{
                {random_query_name_mispelt} {{
                    id
                }}
            }}
        """
        pretty_payload = prettify_graphql_payload(payload)
        return pretty_payload, {}
