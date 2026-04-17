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
        or ``edges`` whose base element type is a known OBJECT.  For Relay-style ``edges``
        fields the resolution descends one extra level through the edge type's ``node`` field
        to return the actual domain object type (e.g. ``Country``, not ``CountryEdge``).
        The resolved type is recorded so the graph generator can wire
        list-query -> inner-object edges.

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
            if inner_base.get("kind") != "OBJECT":
                continue
            inner_type = inner_base.get("type") or inner_base.get("name") or ""
            if not inner_type or inner_type not in objects:
                continue
            # For Relay-style edges, look one level deeper through the edge's `node` field
            if field["name"] == "edges":
                node_type = self._resolve_node_type(inner_type, objects)
                if node_type:
                    return node_type
            return inner_type

        return ""

    def _resolve_node_type(self, edge_type_name: str, objects: dict) -> str:
        """Returns the OBJECT type of the ``node`` field of a Relay edge type, or empty string.

        Args:
            edge_type_name (str): The edge type (e.g. "CountryEdge")
            objects (dict): All compiled objects from the schema

        Returns:
            str: The node's OBJECT type name (e.g. "Country"), or "" if not found
        """
        if edge_type_name not in objects:
            return ""
        for field in objects[edge_type_name].get("fields", []):
            if field["name"] != "node":
                continue
            # Handle both direct OBJECT fields and wrapped (NON_NULL) OBJECT fields
            oftype = field.get("ofType")
            if oftype:
                base = get_base_oftype(oftype)
                if base.get("kind") == "OBJECT":
                    node_type = base.get("type") or base.get("name") or ""
                    if node_type and node_type in objects:
                        return node_type
            if field.get("kind") == "OBJECT":
                node_type = field.get("type") or field.get("name") or ""
                if node_type and node_type in objects:
                    return node_type
        return ""
