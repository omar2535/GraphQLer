"""
This will resolve the inputs of a query to object. A few fields will be introduced to a query, namely:
hardDependsOn: A dictionary of inputname-object name that is required
               in the input (NON-NULL), depends on, ie: {'userId': 'User'}
softDependsOn: A dictionary of inputname-object name, depends on, ie: {'userId': 'User'}
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
        """Resolve query inputs to queries based on semantical understanding of IDs

        Args:
            objects (dict): Objects to link the mutations to
            queries (dict): Queries to parse through
            input_objects (dict): Input objects to recursively search through different input object inputs

        Returns:
            dict: The mutations enriched with aforementioned fields
        """
        for query_name, query in queries.items():
            inputs_related_to_ids = self.get_inputs_related_to_ids(query["inputs"], input_objects)
            resolved_objects_to_inputs = self.resolve_inputs_related_to_ids_to_objects(query_name, inputs_related_to_ids, objects)

            # Assign the enrichments
            queries[query_name]["hardDependsOn"] = resolved_objects_to_inputs["hardDependsOn"]
            queries[query_name]["softDependsOn"] = resolved_objects_to_inputs["softDependsOn"]

        return queries
