from graphqler.fuzzer.engine.materializers.materializer import Materializer
from graphqler.fuzzer.engine.materializers.getter import Getter
from graphqler.fuzzer.engine.materializers.utils.materialization_utils import prettify_graphql_payload
from graphqler.utils.api import API
from graphqler.utils.objects_bucket import ObjectsBucket

from typing import override


class IntrospectionMaterializer(Materializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 20, injection_getter: Getter = Getter()):
        super().__init__(api, fail_on_hard_dependency_not_met, max_depth, injection_getter)
        self.max_depth = max_depth
        self.getter = injection_getter
        self.api = api
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met

    @override
    def get_payload(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str = "") -> tuple[str, dict]:
        """Materializes an introspection query

        Args:
            name (str): The payload name of the Query or Mutation
            objects_bucket (dict): The bucket of objects that have already been created
            graphql_type (str): The type of the graphql operation (Query or Mutation)

        Returns:
            tuple[str, dict]: The string of the payload, and the used objects list
        """
        introspection_query = """
            query {
              __schema {
                queryType { name }
                mutationType { name }
                subscriptionType { name }
              }
            }
        """
        pretty_payload = prettify_graphql_payload(introspection_query)
        return pretty_payload, {}
