"""
This will resolve the inputs of a query to object. A few fields will be introduced to a query, namely:
hardDependsOn: A dictionary of inputname-object name that is required
               in the input (NON-NULL), depends on, ie: {'userId': 'User'}
softDependsOn: A dictionary of inputname-object name, depends on, ie: {'userId': 'User'}
produces:      A string containing the inner object type that a list/connection query produces
               (e.g. 'Country').  Populated when the output type is a connection/wrapper
               whose items/nodes/edges field holds OBJECT elements — used to drive scheduling
               in the dependency graph so list queries run before singular ID-argument queries.
"""

from .resolver import Resolver


class QueryObjectResolver(Resolver):
    def __init__(self):
        super().__init__()

    def resolve(
        self,
        objects: dict,
        queries: dict,
        input_objects: dict,
    ) -> dict:
        """Resolve query inputs to queries based on semantical understanding of IDs.
        Also annotates list/connection queries with a ``produces`` field containing
        the inner item type so the dependency graph can order list queries before
        singular ID-argument queries.

        Args:
            objects (dict): Objects to link the queries to
            queries (dict): Queries to parse through
            input_objects (dict): Input objects to recursively search through different input object inputs

        Returns:
            dict: The queries enriched with aforementioned fields
        """
        for query_name, query in queries.items():
            inputs_related_to_ids = self.get_inputs_related_to_ids(query["inputs"], input_objects)
            resolved_objects_to_inputs = self.resolve_inputs_related_to_ids_to_objects(query_name, inputs_related_to_ids, objects)

            queries[query_name]["hardDependsOn"] = resolved_objects_to_inputs["hardDependsOn"]
            queries[query_name]["softDependsOn"] = resolved_objects_to_inputs["softDependsOn"]
            queries[query_name]["produces"] = self._resolve_produces(query, objects)

        return queries
