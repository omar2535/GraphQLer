"""Unit tests for MutationObjectResolver.produces annotation."""

from graphqler.compiler.resolvers.mutation_object_resolver import MutationObjectResolver


def _make_object(fields):
    return {"kind": "OBJECT", "name": "", "fields": fields}


def _list_field(name, inner_kind, inner_type):
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


def _connection_mutation(outer_type_name):
    """Mutation whose output is a connection wrapper OBJECT."""
    return {
        "name": "createCountries",
        "description": None,
        "inputs": {},
        "output": {
            "kind": "OBJECT",
            "name": outer_type_name,
            "type": outer_type_name,
            "ofType": None,
        },
        "hardDependsOn": {},
        "softDependsOn": {},
    }


class TestMutationObjectResolverProduces:
    def setup_method(self):
        self.resolver = MutationObjectResolver()

    def test_produces_items_field(self):
        """A mutation returning a connection type with ``items`` should produce the inner type."""
        objects = {
            "CountryConnection": _make_object([_list_field("items", "OBJECT", "Country")]),
            "Country": _make_object([]),
        }
        mutation = _connection_mutation("CountryConnection")
        assert self.resolver._resolve_produces(mutation, objects) == "Country"

    def test_produces_nodes_field(self):
        """A mutation returning a connection type with ``nodes`` should produce the inner type."""
        objects = {
            "UserConnection": _make_object([_list_field("nodes", "OBJECT", "User")]),
            "User": _make_object([]),
        }
        mutation = {
            "name": "bulkCreateUsers",
            "description": None,
            "inputs": {},
            "output": {"kind": "OBJECT", "name": "UserConnection", "type": "UserConnection", "ofType": None},
            "hardDependsOn": {},
            "softDependsOn": {},
        }
        assert self.resolver._resolve_produces(mutation, objects) == "User"

    def test_produces_empty_for_plain_object_output(self):
        """A mutation returning a plain OBJECT (not a connection) should not produce an inner type."""
        objects = {
            "Country": _make_object([{"name": "id", "kind": "SCALAR", "type": "ID", "inputs": {}, "ofType": None}]),
        }
        mutation = {
            "name": "createCountry",
            "description": None,
            "inputs": {},
            "output": {"kind": "OBJECT", "name": "Country", "type": "Country", "ofType": None},
            "hardDependsOn": {},
            "softDependsOn": {},
        }
        assert self.resolver._resolve_produces(mutation, objects) == ""

    def test_produces_empty_for_scalar_output(self):
        """A mutation returning a scalar should not produce any inner type."""
        objects = {}
        mutation = {
            "name": "deleteCountry",
            "description": None,
            "inputs": {},
            "output": {"kind": "SCALAR", "name": "Boolean", "type": "Boolean", "ofType": None},
            "hardDependsOn": {},
            "softDependsOn": {},
        }
        assert self.resolver._resolve_produces(mutation, objects) == ""

    def test_resolve_adds_produces_to_all_mutations(self):
        """resolve() should add a ``produces`` key to every mutation."""
        objects = {
            "CountryConnection": _make_object([_list_field("items", "OBJECT", "Country")]),
            "Country": _make_object([]),
        }
        mutations = {
            "createCountries": {
                "name": "createCountries",
                "description": None,
                "inputs": {},
                "output": {"kind": "OBJECT", "name": "CountryConnection", "type": "CountryConnection", "ofType": None},
                "hardDependsOn": {},
                "softDependsOn": {},
            },
            "createCountry": {
                "name": "createCountry",
                "description": None,
                "inputs": {},
                "output": {"kind": "OBJECT", "name": "Country", "type": "Country", "ofType": None},
                "hardDependsOn": {},
                "softDependsOn": {},
            },
        }
        result = self.resolver.resolve(objects, mutations, {})
        assert result["createCountries"]["produces"] == "Country"
        assert result["createCountry"]["produces"] == ""
