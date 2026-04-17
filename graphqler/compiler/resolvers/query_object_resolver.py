"""
This will resolve the inputs of a query to object. A few fields will be introduced to a query, namely:
hardDependsOn: A dictionary of inputname-object name that is required
               in the input (NON-NULL), depends on, ie: {'userId': 'User'}
softDependsOn: A dictionary of inputname-object name, depends on, ie: {'userId': 'User'}
produces:      The inner object type that a list/connection query produces, ie: 'Country'
               (populated when the direct output type is a connection/wrapper wrapping a list
               of objects — used to drive ordering in the dependency graph)
"""

from graphqler.utils.parser_utils import get_base_oftype

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

            # Detect list/connection queries and record the inner item type they produce
            queries[query_name]["produces"] = self._resolve_produces(query, objects)

        return queries

    def _resolve_produces(self, query: dict, objects: dict) -> str:
        """Returns the inner object type produced by a list/connection query, or empty string.

        A query "produces" an inner type when its direct output type is a connection/wrapper
        object (e.g. CountryConnection) that contains a list field named ``items``, ``nodes``,
        or ``edges`` whose base element type is a known OBJECT.  This inner type is recorded
        so the graph generator can wire list-query -> inner-object edges.

        Args:
            query (dict): The compiled query dict (must have an ``output`` key)
            objects (dict): All compiled objects from the schema

        Returns:
            str: The inner object type name (e.g. "Country"), or "" if not applicable
        """
        output = query.get("output", {})
        # Get the base output type (strip NON_NULL / LIST wrappers)
        if output.get("ofType") is not None:
            base_output = get_base_oftype(output["ofType"])
        else:
            base_output = output

        if base_output.get("kind") != "OBJECT":
            return ""

        outer_type_name = base_output.get("type") or base_output.get("name") or ""
        if not outer_type_name or outer_type_name not in objects:
            return ""

        # Look for a connection-wrapper list field in the outer type
        connection_keys = ("items", "nodes", "edges")
        for field in objects[outer_type_name].get("fields", []):
            if field["name"] not in connection_keys:
                continue
            oftype = field.get("ofType")
            if not oftype:
                continue
            inner_base = get_base_oftype(oftype)
            if inner_base.get("kind") == "OBJECT":
                inner_type = inner_base.get("type") or inner_base.get("name") or ""
                if inner_type and inner_type in objects:
                    return inner_type

        return ""
