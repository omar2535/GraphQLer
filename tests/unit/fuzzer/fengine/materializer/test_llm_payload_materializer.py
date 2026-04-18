"""Unit tests for _sanitize_payload and _prune_selection_set in llm_payload_materializer."""

import pytest
from graphql.language.ast import FieldNode
from graphql import parse

from graphqler.fuzzer.engine.materializers.llm_payload_materializer import (
    _prune_selection_set,
    _sanitize_payload,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_selections(payload: str, op_name: str):
    """Return the inner selection list for *op_name* from a query string."""
    from graphql.language.ast import OperationDefinitionNode
    doc = parse(payload)
    op = doc.definitions[0]
    if not isinstance(op, OperationDefinitionNode):
        return []
    for sel in op.selection_set.selections:
        if isinstance(sel, FieldNode) and sel.name.value == op_name:
            if sel.selection_set is None:
                return []
            return sel.selection_set.selections
    return []


# ---------------------------------------------------------------------------
# _prune_selection_set tests
# ---------------------------------------------------------------------------

class TestPruneSelectionSet:
    """Tests for _prune_selection_set."""

    def _selections_of(self, query: str, field: str):
        return _parse_selections(query, field)

    def test_scalar_field_passes_through(self):
        """A known scalar field should be included in the output."""
        schema = {"Post": {"id": "SCALAR", "title": "SCALAR"}}
        sels = self._selections_of("query { post { id title } }", "post")
        result = _prune_selection_set(sels, "Post", schema)
        assert "id" in result
        assert "title" in result

    def test_unknown_field_is_pruned(self):
        """A field not present in the schema should be dropped."""
        schema = {"Post": {"id": "SCALAR"}}
        sels = self._selections_of("query { post { id unknownField } }", "post")
        result = _prune_selection_set(sels, "Post", schema)
        assert "id" in result
        assert "unknownField" not in result

    def test_object_field_without_subselection_is_pruned(self):
        """An OBJECT field with no subselection block should be dropped."""
        schema = {"Post": {"author": "OBJECT:User"}, "User": {"name": "SCALAR"}}
        # `author` has no sub-selection — the parser would reject this in real GraphQL,
        # but we simulate it by checking prune behaviour on a field with an annotation
        # that starts with "OBJECT:" when selections are empty.
        # Here we directly test via a field whose children are all pruned.
        sels = self._selections_of("query { post { author { bogus } } }", "post")
        result = _prune_selection_set(sels, "Post", schema)
        # 'author' has sub-selection but all children are pruned (bogus not in User) → dropped
        assert "author" not in result

    def test_object_field_with_valid_subselection_is_kept(self):
        """An OBJECT field whose subselection survives pruning should be included."""
        schema = {
            "Post": {"author": "OBJECT:User"},
            "User": {"name": "SCALAR"},
        }
        sels = self._selections_of("query { post { author { name } } }", "post")
        result = _prune_selection_set(sels, "Post", schema)
        assert "author" in result
        assert "name" in result

    def test_nested_unknown_type_passes_through(self):
        """When a type is unknown (not in schema), its fields pass through."""
        schema = {}  # empty schema — can't validate anything
        sels = self._selections_of("query { post { id title } }", "post")
        result = _prune_selection_set(sels, "Post", schema)
        # Unknown type → all fields pass through
        assert "id" in result
        assert "title" in result

    def test_empty_selections_returns_empty_string(self):
        """Calling with an empty selections list should return an empty string."""
        schema = {"Post": {"id": "SCALAR"}}
        result = _prune_selection_set([], "Post", schema)
        assert result.strip() == ""

    def test_list_of_scalars_field_passes_through(self):
        """A LIST:SCALAR annotated field should be treated as a scalar leaf."""
        schema = {"Post": {"tags": "LIST:SCALAR"}}
        sels = self._selections_of("query { post { tags } }", "post")
        result = _prune_selection_set(sels, "Post", schema)
        assert "tags" in result

    def test_list_of_objects_with_valid_subselection(self):
        """A LIST:ObjectType field whose children survive pruning should be included."""
        schema = {
            "Post": {"comments": "LIST:Comment"},
            "Comment": {"body": "SCALAR"},
        }
        sels = self._selections_of("query { post { comments { body } } }", "post")
        result = _prune_selection_set(sels, "Post", schema)
        assert "comments" in result
        assert "body" in result


# ---------------------------------------------------------------------------
# _sanitize_payload tests
# ---------------------------------------------------------------------------

def _make_operator_info(root_type: str):
    """Build minimal operator_info pointing output to root_type."""
    return {"output": {"kind": "OBJECT", "type": root_type}}


class TestSanitizePayload:
    """Tests for _sanitize_payload."""

    def test_valid_payload_passes_through(self):
        """A fully valid payload should be returned (possibly prettified) unchanged."""
        schema = {"Post": {"id": "SCALAR", "title": "SCALAR"}}
        payload = "query { getPost { id title } }"
        result = _sanitize_payload(payload, "getPost", "Query", _make_operator_info("Post"), schema)
        assert "id" in result
        assert "title" in result

    def test_unknown_field_pruned_from_payload(self):
        """Fields not in schema should be stripped from the returned payload."""
        schema = {"Post": {"id": "SCALAR"}}
        payload = "query { getPost { id secret } }"
        result = _sanitize_payload(payload, "getPost", "Query", _make_operator_info("Post"), schema)
        assert "id" in result
        assert "secret" not in result

    def test_object_without_subselection_pruned(self):
        """Object field missing its subselection should be removed by pruning."""
        schema = {
            "Post": {"author": "OBJECT:User"},
            "User": {"unknownOnly": "SCALAR"},  # 'unknownOnly' won't match real field
        }
        # 'author' block contains only an unknown field → should be pruned
        payload = "query { getPost { author { bogus } } }"
        # Pruning author leaves empty selection → raises ValueError
        with pytest.raises(ValueError):
            _sanitize_payload(payload, "getPost", "Query", _make_operator_info("Post"), schema)

    def test_all_fields_pruned_raises_value_error(self):
        """If pruning removes every field, ValueError should be raised."""
        schema = {"Post": {"id": "SCALAR"}}
        payload = "query { getPost { bogus1 bogus2 } }"
        with pytest.raises(ValueError, match="All output fields pruned"):
            _sanitize_payload(payload, "getPost", "Query", _make_operator_info("Post"), schema)

    def test_no_root_type_returns_payload_as_is(self):
        """Without root type info, the payload should be returned unchanged."""
        schema = {"Post": {"id": "SCALAR"}}
        payload = "query { getPost { id } }"
        operator_info = {}  # no 'output' key
        result = _sanitize_payload(payload, "getPost", "Query", operator_info, schema)
        assert result == payload

    def test_root_type_not_in_schema_returns_as_is(self):
        """If root_type is not present in output_schema, payload is returned unchanged."""
        schema = {}  # Post not in schema
        payload = "query { getPost { id title } }"
        result = _sanitize_payload(payload, "getPost", "Query", _make_operator_info("Post"), schema)
        assert result == payload

    def test_operation_field_not_found_returns_as_is(self):
        """If the named operation field isn't in the selection, return unchanged."""
        schema = {"Post": {"id": "SCALAR"}}
        payload = "query { differentField { id } }"
        result = _sanitize_payload(payload, "getPost", "Query", _make_operator_info("Post"), schema)
        assert result == payload

    def test_mutation_type_handled(self):
        """Mutation graphql_type should be handled just like Query."""
        schema = {"Post": {"id": "SCALAR", "title": "SCALAR"}}
        payload = "mutation { createPost { id title secret } }"
        result = _sanitize_payload(payload, "createPost", "Mutation", _make_operator_info("Post"), schema)
        assert "id" in result
        assert "title" in result
        assert "secret" not in result
