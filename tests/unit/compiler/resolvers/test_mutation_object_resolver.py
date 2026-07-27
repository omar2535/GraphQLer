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


class TestMutationPayloadWrapperIdDependency:
    """A bare 'id' input must resolve to the resource, not the mutation's payload type.

    GraphQL mutations conventionally return an envelope named after the mutation
    (deleteNote -> DeleteNote). Inferring the ID dependency from that output makes
    the mutation depend on its own result, which detaches DELETE operations from
    the CREATE that produced the resource and silently disables the IDOR and UAF
    chain strategies.
    """

    def setup_method(self):
        self.resolver = MutationObjectResolver()

    def _idor_api_objects(self):
        return {
            "Note": _make_object([]),
            "Order": _make_object([]),
            "DeleteNote": _make_object([]),
            "DeleteOrder": _make_object([]),
        }

    def _object_output(self, type_name):
        return {"kind": "OBJECT", "name": type_name, "type": type_name, "ofType": None}

    def test_delete_mutation_id_resolves_to_resource_not_payload(self):
        objects = self._idor_api_objects()
        operation = {"output": self._object_output("DeleteNote")}
        result = self.resolver.resolve_inputs_related_to_ids_to_objects(
            "deleteNote", {"id": True}, objects, operation=operation
        )
        assert result["hardDependsOn"].get("id") == "Note"

    def test_delete_mutation_payload_wrapper_not_self_referential(self):
        objects = self._idor_api_objects()
        operation = {"output": self._object_output("DeleteOrder")}
        result = self.resolver.resolve_inputs_related_to_ids_to_objects(
            "deleteOrder", {"id": True}, objects, operation=operation
        )
        assert result["hardDependsOn"].get("id") != "DeleteOrder"
        assert result["hardDependsOn"].get("id") == "Order"

    def test_mutation_returning_resource_directly_still_uses_output(self):
        """When the output is the resource itself, output inference is correct."""
        objects = self._idor_api_objects()
        operation = {"output": self._object_output("Note")}
        result = self.resolver.resolve_inputs_related_to_ids_to_objects(
            "updateNote", {"id": True}, objects, operation=operation
        )
        assert result["hardDependsOn"].get("id") == "Note"

    def test_object_name_beginning_with_verb_is_not_treated_as_wrapper(self):
        """'Setting' starts with a CRUD verb but is a real type, so it is kept."""
        objects = {"Setting": _make_object([])}
        operation = {"output": self._object_output("Setting")}
        result = self.resolver.resolve_inputs_related_to_ids_to_objects(
            "fetchConfig", {"id": True}, objects, operation=operation
        )
        assert result["hardDependsOn"].get("id") == "Setting"
