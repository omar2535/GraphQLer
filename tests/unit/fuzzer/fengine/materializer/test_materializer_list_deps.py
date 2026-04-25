"""Unit tests for Materializer.materialize_input_recursive focusing on:
- _input_has_list_type helper
- LIST wrapping for dependency-resolved values (hard and soft)
- Full-stack materialization of a *ByIds query (charactersByIds pattern)
"""

from unittest.mock import MagicMock

from graphqler.fuzzer.engine.materializers.materializer import Materializer
from graphqler.fuzzer.engine.materializers.getter import Getter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scalar_id_field(name="id"):
    return {"name": name, "kind": "SCALAR", "type": "ID", "ofType": None}


def _non_null_list_id_input(name="ids"):
    """NON_NULL > LIST > NON_NULL > SCALAR(ID)  — equivalent to [ID!]!"""
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


def _make_materializer() -> Materializer:
    api = MagicMock()
    api.queries = {}
    api.mutations = {}
    api.objects = {}
    api.input_objects = {}
    api.enums = {}
    api.unions = {}
    api.interfaces = {}
    getter = Getter()
    m = Materializer.__new__(Materializer)
    m.api = api
    m.fail_on_hard_dependency_not_met = True
    m.used_objects = {}
    m.max_depth = 5
    m.getter = getter
    m.logger = MagicMock()
    return m


def _make_bucket(objects_map: dict) -> MagicMock:
    """Return a mock bucket with controlled per-object field lookups."""
    bucket = MagicMock()
    bucket.is_empty.return_value = False

    def _is_in(name):
        return name in objects_map and len(objects_map[name]) > 0

    def _get_field(obj, field):
        if obj not in objects_map:
            raise Exception("Object not found in bucket")
        return objects_map[obj].get(field, None)

    bucket.is_object_in_bucket.side_effect = _is_in
    bucket.get_random_object_field_value.side_effect = _get_field
    return bucket


# ---------------------------------------------------------------------------
# _input_has_list_type
# ---------------------------------------------------------------------------

class TestInputHasListType:
    def setup_method(self):
        self.m = _make_materializer()

    def test_scalar_has_no_list(self):
        assert self.m._input_has_list_type(_scalar_id_field()) is False

    def test_non_null_scalar_has_no_list(self):
        field = {"name": "id", "kind": "NON_NULL", "type": None, "ofType": _scalar_id_field()}
        assert self.m._input_has_list_type(field) is False

    def test_list_detected_directly(self):
        field = {"name": "ids", "kind": "LIST", "type": None, "ofType": _scalar_id_field()}
        assert self.m._input_has_list_type(field) is True

    def test_non_null_wrapping_list_detected(self):
        """NON_NULL > LIST > SCALAR — still contains a LIST."""
        field = _non_null_list_id_input()
        assert self.m._input_has_list_type(field) is True

    def test_deeply_nested_list_detected(self):
        """NON_NULL > NON_NULL > LIST > SCALAR."""
        inner = {"name": "x", "kind": "LIST", "type": None, "ofType": _scalar_id_field()}
        outer = {"name": "x", "kind": "NON_NULL", "type": None, "ofType": inner}
        assert self.m._input_has_list_type(outer) is True


# ---------------------------------------------------------------------------
# LIST wrapping in hard-dependency resolution
# ---------------------------------------------------------------------------

class TestMaterializeInputRecursiveListWrapping:
    def setup_method(self):
        self.m = _make_materializer()

    def test_scalar_dependency_not_wrapped(self):
        """A plain ID dependency (no LIST) should produce a quoted scalar, not a list."""
        operator_info = {"hardDependsOn": {"id": "Character"}, "softDependsOn": {}}
        input_field = {"name": "id", "kind": "NON_NULL", "type": None, "ofType": _scalar_id_field()}
        bucket = _make_bucket({"Character": {"id": "42"}})

        result = self.m.materialize_input_recursive(operator_info, input_field, bucket, "id", True, 5, 1)

        assert result == '"42"'

    def test_list_dependency_wrapped_in_brackets(self):
        """A [ID!]! dependency should produce a list literal like [\"1\"]."""
        operator_info = {"hardDependsOn": {"ids": "Character"}, "softDependsOn": {}}
        input_field = _non_null_list_id_input("ids")
        bucket = _make_bucket({"Character": {"id": "1"}})

        result = self.m.materialize_input_recursive(operator_info, input_field, bucket, "ids", True, 5, 1)

        assert result == '["1"]'

    def test_soft_dependency_list_wrapped(self):
        """Soft dependency on a list type should also be wrapped in [...]."""
        operator_info = {"hardDependsOn": {}, "softDependsOn": {"ids": "Episode"}}
        input_field = _non_null_list_id_input("ids")
        bucket = _make_bucket({"Episode": {"id": "7"}})

        result = self.m.materialize_input_recursive(operator_info, input_field, bucket, "ids", True, 5, 1)

        assert result == '["7"]'

    def test_list_wrapping_uses_singular_fallback(self):
        """When the bucket has 'id' but the input is 'ids', singular fallback + list wrap."""
        operator_info = {"hardDependsOn": {"ids": "Character"}, "softDependsOn": {}}
        input_field = _non_null_list_id_input("ids")
        # The Character object only has 'id', not 'ids'
        bucket = _make_bucket({"Character": {"id": "99"}})

        result = self.m.materialize_input_recursive(operator_info, input_field, bucket, "ids", True, 5, 1)

        assert result == '["99"]'
