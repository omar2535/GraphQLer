"""Unit tests for QueryObjectResolver._resolve_produces"""

import pytest

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
        """A Relay-style connection type with an ``edges`` list field should produce the edge's inner type."""
        objects = {
            "PostConnection": _make_object([_list_field("edges", "OBJECT", "PostEdge")]),
            "PostEdge": _make_object([]),
        }
        query = {
            "name": "posts",
            "inputs": {},
            "output": {"kind": "OBJECT", "name": "PostConnection", "type": "PostConnection", "ofType": None},
        }
        # PostEdge is in objects, so produces should be "PostEdge"
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

    def test_resolve_adds_produces_to_all_queries(self):
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
