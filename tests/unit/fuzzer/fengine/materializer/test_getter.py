"""Unit tests for Getter.get_closest_value_to_input, focusing on the plural→singular fallback."""

import pytest
from unittest.mock import MagicMock

from graphqler.fuzzer.engine.materializers.getter import Getter


def _make_bucket(object_name: str, field_values: dict) -> MagicMock:
    """Return a mock ObjectsBucket that maps field_name → value for *object_name*.

    ``field_values`` maps field_name → return value (or None to simulate missing field).
    The mock raises ``Exception("Object not found in bucket")`` if the object is not listed
    (matching the real behaviour of ObjectsBucket.get_random_object_field_value).
    """
    bucket = MagicMock()
    bucket.is_empty.return_value = False

    def _get_field(obj, field):
        if obj != object_name:
            raise Exception("Object not found in bucket")
        return field_values.get(field, None)

    bucket.get_random_object_field_value.side_effect = _get_field
    return bucket


class TestGetterClosestValueSingularFallback:
    def setup_method(self):
        self.getter = Getter()

    def test_exact_match_returned_directly(self):
        """When the field exists by exact name, it is returned without fallback."""
        bucket = _make_bucket("Character", {"id": "42"})
        result = self.getter.get_closest_value_to_input("id", "Character", bucket)
        assert result == "42"

    def test_ids_falls_back_to_id(self):
        """'ids' input resolves to the 'id' field of the object via singular fallback."""
        # The Character object has 'id' but not 'ids'
        bucket = _make_bucket("Character", {"id": "1"})
        result = self.getter.get_closest_value_to_input("ids", "Character", bucket)
        assert result == "1"

    def test_episodes_ids_falls_back_to_id(self):
        """Works the same way for Episode objects."""
        bucket = _make_bucket("Episode", {"id": "7"})
        result = self.getter.get_closest_value_to_input("ids", "Episode", bucket)
        assert result == "7"

    def test_no_fallback_when_field_truly_missing(self):
        """Exception is raised when neither 'ids' nor 'id' exist on the object."""
        bucket = _make_bucket("Character", {})  # no fields at all
        with pytest.raises(Exception, match="Could not find a value"):
            self.getter.get_closest_value_to_input("ids", "Character", bucket)

    def test_non_plural_missing_field_raises(self):
        """Non-plural missing field (no trailing 's') still raises the original exception."""
        bucket = _make_bucket("Character", {})
        with pytest.raises(Exception, match="Could not find a value"):
            self.getter.get_closest_value_to_input("name", "Character", bucket)
