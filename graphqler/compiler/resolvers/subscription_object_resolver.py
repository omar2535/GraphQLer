"""
Resolves subscription inputs to objects. Subscriptions have the same ID-based
dependency structure as queries, so this resolver delegates entirely to
QueryObjectResolver's logic.
"""

from .query_object_resolver import QueryObjectResolver


class SubscriptionObjectResolver(QueryObjectResolver):
    def __init__(self):
        super().__init__()

    def resolve(
        self,
        objects: dict,
        queries: dict,
        input_objects: dict,
    ) -> dict:
        """Resolve subscription inputs to objects based on semantic ID matching.

        Args:
            objects (dict): Objects to link subscriptions to
            queries (dict): Subscriptions to enrich (named 'queries' to match parent signature)
            input_objects (dict): Input objects for recursive input resolution

        Returns:
            dict: Subscriptions enriched with hardDependsOn and softDependsOn
        """
        subscriptions = queries
        for subscription_name, subscription in subscriptions.items():
            inputs_related_to_ids = self.get_inputs_related_to_ids(subscription["inputs"], input_objects)
            resolved_objects_to_inputs = self.resolve_inputs_related_to_ids_to_objects(subscription_name, inputs_related_to_ids, objects)

            subscriptions[subscription_name]["hardDependsOn"] = resolved_objects_to_inputs["hardDependsOn"]
            subscriptions[subscription_name]["softDependsOn"] = resolved_objects_to_inputs["softDependsOn"]

        return subscriptions
