"""Subscription payload materializer.

Builds a ``subscription { ... }`` operation string using the same input/output
materialization logic as :class:`RegularPayloadMaterializer`, but keyed off
``api.subscriptions`` instead of ``api.queries``.
"""

from .materializer import Materializer
from .utils.materialization_utils import prettify_graphql_payload
from .getter import Getter
from graphqler.config import MAX_OUTPUT_SELECTOR_DEPTH, MAX_INPUT_DEPTH
from graphqler.utils.api import API
from graphqler.utils.objects_bucket import ObjectsBucket


class SubscriptionMaterializer(Materializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = True):
        self.getters = Getter()
        self.api = api
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        super().__init__(self.api, self.fail_on_hard_dependency_not_met, max_depth=MAX_OUTPUT_SELECTOR_DEPTH, getter=self.getters)

    def get_payload(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str) -> tuple[str, dict]:
        """Materializes a subscription payload with parameters filled in.

        Args:
            name (str): Subscription name
            objects_bucket (ObjectsBucket): Bucket of objects available at runtime
            graphql_type (str): Should be "Subscription"

        Returns:
            tuple[str, dict]: The subscription payload string and the used objects dict
        """
        self.used_objects = {}
        return self._get_subscription_payload(name, objects_bucket, max_input_depth=MAX_INPUT_DEPTH, max_output_depth=MAX_OUTPUT_SELECTOR_DEPTH)

    def _get_subscription_payload(
        self,
        subscription_name: str,
        objects_bucket: ObjectsBucket,
        max_input_depth: int = MAX_INPUT_DEPTH,
        max_output_depth: int = MAX_OUTPUT_SELECTOR_DEPTH,
    ) -> tuple[str, dict]:
        subscription_info = self.api.subscriptions[subscription_name]
        subscription_inputs = self.materialize_inputs(subscription_info, subscription_info["inputs"], objects_bucket, max_depth=max_input_depth)
        subscription_output = self.materialize_output(subscription_info, subscription_info["output"], objects_bucket, max_depth=max_output_depth, minimal_materialization=True)

        if subscription_inputs != "":
            subscription_inputs = f"({subscription_inputs})"

        payload = f"""
        subscription {{
            {subscription_name} {subscription_inputs}
            {subscription_output}
        }}
        """
        pretty_payload = prettify_graphql_payload(payload)
        return pretty_payload, self.used_objects
