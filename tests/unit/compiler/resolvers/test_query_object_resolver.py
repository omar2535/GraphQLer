"""Unit tests for QueryObjectResolver._resolve_produces and ids dependency resolution."""

from graphqler.compiler.resolvers.query_object_resolver import QueryObjectResolver


def _make_object(fields):
    """Helper to build a compiled object dict."""
    return {"kind": "OBJECT", "name": "", "fields": fields}


def _list_field(name, inner_kind, inner_type):
    """Helper to build a LIST field entry like the object_list_parser produces."""
    return {
        "name": name,
        "kind": "LIST",
        "type": None,
        "inputs": {},
        "ofType": {
            "kind": "LIST",
            "name": None,
            "type": None,
            "ofType": {
                "kind": inner_kind,
                "name": inner_type,
                "type": inner_type,
                "ofType": None,
            },
        },
    }


def _connection_query(outer_type_name):
    """Query whose output is a connection wrapper OBJECT."""
    return {
        "name": "countries",
        "inputs": {},
        "output": {
            "kind": "OBJECT",
            "name": outer_type_name,
            "type": outer_type_name,
            "ofType": None,
        },
    }


class TestQueryObjectResolverProduces:
    def setup_method(self):
        self.resolver = QueryObjectResolver()

    def test_produces_items_field(self):
        """A connection type with an ``items`` list field should produce the inner type."""
        objects = {
            "CountryConnection": _make_object([_list_field("items", "OBJECT", "Country")]),
            "Country": _make_object([]),
        }
        query = _connection_query("CountryConnection")
        assert self.resolver._resolve_produces(query, objects) == "Country"

    def test_produces_nodes_field(self):
        """A connection type with a ``nodes`` list field should produce the inner type."""
        objects = {
            "UserConnection": _make_object([_list_field("nodes", "OBJECT", "User")]),
            "User": _make_object([]),
        }
        query = {
            "name": "users",
            "inputs": {},
            "output": {"kind": "OBJECT", "name": "UserConnection", "type": "UserConnection", "ofType": None},
        }
        assert self.resolver._resolve_produces(query, objects) == "User"

    def test_produces_edges_field(self):
        """A Relay-style connection type with ``edges`` should produce the node's domain type (Post, not PostEdge)."""
        post_edge_node_field = {
            "name": "node",
            "kind": "OBJECT",
            "type": "Post",
            "inputs": {},
            "ofType": None,
        }
        objects = {
            "PostConnection": _make_object([_list_field("edges", "OBJECT", "PostEdge")]),
            "PostEdge": _make_object([post_edge_node_field]),
            "Post": _make_object([]),
        }
        query = {
            "name": "posts",
            "inputs": {},
            "output": {"kind": "OBJECT", "name": "PostConnection", "type": "PostConnection", "ofType": None},
        }
        # For Relay edges, _resolve_produces must descend through PostEdge.node -> Post
        assert self.resolver._resolve_produces(query, objects) == "Post"

    def test_produces_edges_without_node_falls_back_to_edge_type(self):
        """When an edge type has no ``node`` field, the edge type itself is used as a fallback."""
        objects = {
            "PostConnection": _make_object([_list_field("edges", "OBJECT", "PostEdge")]),
            "PostEdge": _make_object([]),  # no node field
        }
        query = {
            "name": "posts",
            "inputs": {},
            "output": {"kind": "OBJECT", "name": "PostConnection", "type": "PostConnection", "ofType": None},
        }
        assert self.resolver._resolve_produces(query, objects) == "PostEdge"

    def test_produces_empty_for_scalar_output(self):
        """A query returning a scalar should not produce any inner type."""
        objects = {}
        query = {
            "name": "ping",
            "inputs": {},
            "output": {"kind": "SCALAR", "name": "String", "type": "String", "ofType": None},
        }
        assert self.resolver._resolve_produces(query, objects) == ""

    def test_produces_empty_when_outer_type_not_in_objects(self):
        """No inner type if the outer connection type is not in the objects registry."""
        objects = {}
        query = _connection_query("UnknownConnection")
        assert self.resolver._resolve_produces(query, objects) == ""

    def test_produces_empty_when_no_connection_fields(self):
        """A plain OBJECT output with no items/nodes/edges fields should return empty."""
        objects = {
            "Country": _make_object([{"name": "id", "kind": "SCALAR", "type": "ID", "inputs": {}, "ofType": None}]),
        }
        query = {
            "name": "country",
            "inputs": {},
            "output": {"kind": "OBJECT", "name": "Country", "type": "Country", "ofType": None},
        }
        assert self.resolver._resolve_produces(query, objects) == ""

    def test_produces_results_field(self):
        """A Rick-and-Morty-style wrapper with a ``results`` list field produces the inner type."""
        objects = {
            "Characters": _make_object([_list_field("results", "OBJECT", "Character")]),
            "Character": _make_object([]),
        }
        query = {
            "name": "characters",
            "inputs": {},
            "output": {"kind": "OBJECT", "name": "Characters", "type": "Characters", "ofType": None},
        }
        assert self.resolver._resolve_produces(query, objects) == "Character"

    def test_produces_auto_discovered_non_standard_list_field(self):
        """A wrapper with a non-standard list field name (e.g. ``data``) is auto-discovered."""
        objects = {
            "WidgetList": _make_object([_list_field("data", "OBJECT", "Widget")]),
            "Widget": _make_object([]),
        }
        query = {
            "name": "widgets",
            "inputs": {},
            "output": {"kind": "OBJECT", "name": "WidgetList", "type": "WidgetList", "ofType": None},
        }
        assert self.resolver._resolve_produces(query, objects) == "Widget"


        """resolve() should add a ``produces`` key to every query."""
        objects = {
            "CountryConnection": _make_object([_list_field("items", "OBJECT", "Country")]),
            "Country": _make_object([]),
        }
        queries = {
            "countries": {
                "name": "countries",
                "inputs": {},
                "output": {"kind": "OBJECT", "name": "CountryConnection", "type": "CountryConnection", "ofType": None},
                "hardDependsOn": {},
                "softDependsOn": {},
            },
            "country": {
                "name": "country",
                "inputs": {"id": {"name": "id", "kind": "NON_NULL", "type": "ID", "ofType": {"kind": "SCALAR", "name": "ID", "type": "ID", "ofType": None}}},
                "output": {"kind": "OBJECT", "name": "Country", "type": "Country", "ofType": None},
                "hardDependsOn": {},
                "softDependsOn": {},
            },
        }
        result = self.resolver.resolve(objects, queries, {})
        assert result["countries"]["produces"] == "Country"
        assert result["country"]["produces"] == ""


# ---------------------------------------------------------------------------
# Tests for ids dependency resolution (Rick-and-Morty-style *ByIds queries)
# ---------------------------------------------------------------------------

def _non_null_list_id_input(name: str) -> dict:
    """Build a compiled input field for ``name: [ID!]!`` (NON_NULL > LIST > NON_NULL > SCALAR)."""
    return {
        "name": name,
        "kind": "NON_NULL",
        "type": None,
        "ofType": {
            "kind": "LIST",
            "name": None,
            "type": None,
            "ofType": {
                "kind": "NON_NULL",
                "name": None,
                "type": None,
                "ofType": {
                    "kind": "SCALAR",
                    "name": "ID",
                    "type": "ID",
                    "ofType": None,
                },
            },
        },
    }


class TestQueryObjectResolverIdsDependency:
    """Tests for resolve_inputs_related_to_ids_to_objects with plural 'ids' input."""

    def setup_method(self):
        self.resolver = QueryObjectResolver()

    def _objects_rick_and_morty(self):
        return {
            "Character": _make_object([]),
            "Characters": _make_object([]),
            "Episode": _make_object([]),
            "Episodes": _make_object([]),
            "Location": _make_object([]),
            "Locations": _make_object([]),
        }

    def _list_output(self, type_name: str) -> dict:
        """Build a compiled LIST output (equivalent to [TypeName])."""
        return {
            "kind": "LIST",
            "name": None,
            "type": None,
            "ofType": {"kind": "OBJECT", "name": type_name, "type": type_name, "ofType": None},
        }

    def _non_null_list_output(self, type_name: str) -> dict:
        """Build a compiled NON_NULL(LIST(OBJECT)) output (equivalent to [TypeName]!)."""
        return {
            "kind": "NON_NULL",
            "name": None,
            "type": None,
            "ofType": {
                "kind": "LIST",
                "name": None,
                "type": None,
                "ofType": {"kind": "OBJECT", "name": type_name, "type": type_name, "ofType": None},
            },
        }

    # ------------------------------------------------------------------
    # Output-type inference (primary path)
    # ------------------------------------------------------------------

    def test_output_type_inference_for_ids(self):
        """ids → Object is derived from the operation's output type, not its name."""
        objects = self._objects_rick_and_morty()
        operation = {"output": self._list_output("Character")}
        result = self.resolver.resolve_inputs_related_to_ids_to_objects(
            "fetchNodesByKey", {"ids": True}, objects, operation=operation
        )
        assert result["hardDependsOn"].get("ids") == "Character"

    def test_output_type_inference_for_id(self):
        """Bare 'id' input also uses the output type when provided."""
        objects = self._objects_rick_and_morty()
        operation = {"output": {"kind": "OBJECT", "name": "Character", "type": "Character", "ofType": None}}
        result = self.resolver.resolve_inputs_related_to_ids_to_objects(
            "getNodeByKey", {"id": True}, objects, operation=operation
        )
        assert result["hardDependsOn"].get("id") == "Character"

    def test_output_type_non_null_list_inference(self):
        """NON_NULL(LIST(OBJECT)) output type is resolved to the inner OBJECT."""
        objects = self._objects_rick_and_morty()
        operation = {"output": self._non_null_list_output("Episode")}
        result = self.resolver.resolve_inputs_related_to_ids_to_objects(
            "episodesByIds", {"ids": True}, objects, operation=operation
        )
        assert result["hardDependsOn"].get("ids") == "Episode"

    def test_output_type_inference_ignores_endpoint_name(self):
        """Output-type inference works even when the endpoint name has no relation to the type."""
        objects = {"Widget": _make_object([]), "Gadget": _make_object([])}
        operation = {"output": {"kind": "LIST", "name": None, "type": None,
                                "ofType": {"kind": "OBJECT", "name": "Widget", "type": "Widget", "ofType": None}}}
        result = self.resolver.resolve_inputs_related_to_ids_to_objects(
            "arbitraryEndpointName", {"ids": True}, objects, operation=operation
        )
        assert result["hardDependsOn"].get("ids") == "Widget"

    # ------------------------------------------------------------------
    # Name-based fallback (no operation provided)
    # ------------------------------------------------------------------

    def test_fallback_characters_by_ids_resolves_to_character(self):
        """Without an operation, charactersByIds.ids resolves to Character via name heuristic."""
        objects = self._objects_rick_and_morty()
        result = self.resolver.resolve_inputs_related_to_ids_to_objects(
            "charactersByIds", {"ids": True}, objects
        )
        assert result["hardDependsOn"].get("ids") == "Character"

    def test_fallback_episodes_by_ids_resolves_to_episode(self):
        objects = self._objects_rick_and_morty()
        result = self.resolver.resolve_inputs_related_to_ids_to_objects(
            "episodesByIds", {"ids": True}, objects
        )
        assert result["hardDependsOn"].get("ids") == "Episode"

    def test_fallback_locations_by_ids_resolves_to_location(self):
        objects = self._objects_rick_and_morty()
        result = self.resolver.resolve_inputs_related_to_ids_to_objects(
            "locationsByIds", {"ids": True}, objects
        )
        assert result["hardDependsOn"].get("ids") == "Location"

    def test_soft_ids_dependency_via_output_type(self):
        """A nullable ids input with output type produces a soft dep on the item type."""
        objects = self._objects_rick_and_morty()
        operation = {"output": self._list_output("Character")}
        result = self.resolver.resolve_inputs_related_to_ids_to_objects(
            "charactersByIds", {"ids": False}, objects, operation=operation
        )
        assert result["softDependsOn"].get("ids") == "Character"
        assert "ids" not in result["hardDependsOn"]

    # ------------------------------------------------------------------
    # Full resolve() integration
    # ------------------------------------------------------------------

    def test_resolve_integrates_with_full_query(self):
        """resolve() passes the operation to the resolver so ids → output-type Object."""
        objects = self._objects_rick_and_morty()
        queries = {
            "charactersByIds": {
                "name": "charactersByIds",
                "inputs": {"ids": _non_null_list_id_input("ids")},
                "output": self._list_output("Character"),
                "hardDependsOn": {},
                "softDependsOn": {},
            }
        }
        result = self.resolver.resolve(objects, queries, {})
        assert result["charactersByIds"]["hardDependsOn"].get("ids") == "Character"

    def test_resolve_unconventional_name_still_works(self):
        """When the endpoint name has no relation to the type, output-type inference saves it."""
        objects = {"Widget": _make_object([]), "Gadget": _make_object([])}
        queries = {
            "fetchSomethingByKeys": {
                "name": "fetchSomethingByKeys",
                "inputs": {"ids": _non_null_list_id_input("ids")},
                "output": {
                    "kind": "NON_NULL",
                    "name": None,
                    "type": None,
                    "ofType": {
                        "kind": "LIST",
                        "name": None,
                        "type": None,
                        "ofType": {"kind": "OBJECT", "name": "Widget", "type": "Widget", "ofType": None},
                    },
                },
                "hardDependsOn": {},
                "softDependsOn": {},
            }
        }
        result = self.resolver.resolve(objects, queries, {})
        assert result["fetchSomethingByKeys"]["hardDependsOn"].get("ids") == "Widget"

