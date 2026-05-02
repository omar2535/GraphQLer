"""Unit tests for the three new DoS materializers and detectors."""

import unittest
from unittest.mock import MagicMock

from graphqler.fuzzer.engine.materializers.dos.dos_field_duplication_materializer import (
    DOSFieldDuplicationMaterializer,
    FIELD_DUPLICATION_COUNT,
)
from graphqler.fuzzer.engine.materializers.dos.dos_circular_fragment_materializer import (
    DOSCircularFragmentMaterializer,
)
from graphqler.fuzzer.engine.materializers.dos.dos_resource_exhaustion_materializer import (
    DOSResourceExhaustionMaterializer,
    ResourceExhaustionGetter,
    LARGE_PAGINATION_VALUE,
    PAGINATION_INPUT_NAMES,
)
from graphqler.fuzzer.engine.detectors.dos.dos_detector_base import (
    DOS_SAFE_REJECTION_PATTERNS,
)
from graphqler.fuzzer.engine.detectors.dos.field_duplication_detector import FieldDuplicationDetector
from graphqler.fuzzer.engine.detectors.dos.circular_fragment_detector import CircularFragmentDetector
from graphqler.fuzzer.engine.detectors.dos.resource_exhaustion_detector import ResourceExhaustionDetector


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_api(query_output: dict | None = None, objects: dict | None = None, inputs: dict | None = None):
    """Build a minimal mock API object.

    query_output  - the ``output`` dict for the ``getUser`` query
    objects       - the ``api.objects`` mapping
    inputs        - the ``inputs`` dict for the ``getUser`` query
    """
    api = MagicMock()
    api.url = "http://localhost/graphql"

    if query_output is None:
        query_output = {
            "kind": "OBJECT",
            "name": "getUser",
            "ofType": None,
            "type": "User",
        }
    if objects is None:
        objects = {
            "User": {
                "fields": [
                    {"kind": "SCALAR", "name": "id", "ofType": None, "type": "String"},
                    {"kind": "SCALAR", "name": "name", "ofType": None, "type": "String"},
                ]
            }
        }
    if inputs is None:
        inputs = {}

    api.objects = objects
    api.queries = {
        "getUser": {
            "inputs": inputs,
            "output": query_output,
            "hardDependsOn": {},
            "softDependsOn": {},
        }
    }
    api.mutations = {}
    return api


def _make_objects_bucket():
    bucket = MagicMock()
    bucket.is_object_in_bucket.return_value = False
    bucket.get_random_object_id.return_value = "mock-id"
    return bucket


# ---------------------------------------------------------------------------
# DOSFieldDuplicationMaterializer
# ---------------------------------------------------------------------------

class TestDOSFieldDuplicationMaterializer(unittest.TestCase):

    def _materializer(self, api=None):
        if api is None:
            api = _make_api()
        return DOSFieldDuplicationMaterializer(api=api, fail_on_hard_dependency_not_met=False)

    def test_payload_contains_aliased_field_repetitions(self):
        mat = self._materializer()
        payload, _ = mat.get_payload("getUser", _make_objects_bucket(), graphql_type="Query")
        # Should contain at least FIELD_DUPLICATION_COUNT aliases for the first scalar field
        assert "f0: id" in payload
        assert f"f{FIELD_DUPLICATION_COUNT - 1}: id" in payload

    def test_payload_is_valid_graphql_structure(self):
        mat = self._materializer()
        payload, _ = mat.get_payload("getUser", _make_objects_bucket(), graphql_type="Query")
        assert "getUser" in payload

    def test_fallback_when_no_scalar_field_available(self):
        """When the output type has no scalar fields, should not raise."""
        api = _make_api(
            objects={"User": {"fields": []}}  # no scalar fields
        )
        mat = DOSFieldDuplicationMaterializer(api=api, fail_on_hard_dependency_not_met=False)
        # Should not raise; falls back to normal materialisation
        try:
            payload, _ = mat.get_payload("getUser", _make_objects_bucket(), graphql_type="Query")
        except Exception as exc:
            self.fail(f"get_payload raised unexpectedly: {exc}")

    def test_raises_on_invalid_graphql_type(self):
        mat = self._materializer()
        with self.assertRaises(ValueError):
            mat.get_payload("getUser", _make_objects_bucket(), graphql_type="Subscription")

    def test_number_of_aliased_fields(self):
        mat = self._materializer()
        payload, _ = mat.get_payload("getUser", _make_objects_bucket(), graphql_type="Query")
        count = sum(1 for line in payload.splitlines() if ": id" in line)
        self.assertEqual(count, FIELD_DUPLICATION_COUNT)


# ---------------------------------------------------------------------------
# DOSCircularFragmentMaterializer
# ---------------------------------------------------------------------------

class TestDOSCircularFragmentMaterializer(unittest.TestCase):

    def _materializer(self, api=None):
        if api is None:
            api = _make_api()
        return DOSCircularFragmentMaterializer(api=api, fail_on_hard_dependency_not_met=False)

    def test_payload_contains_two_mutually_referencing_fragments(self):
        mat = self._materializer()
        payload, _ = mat.get_payload("getUser", _make_objects_bucket(), graphql_type="Query")
        assert "fragment CircFragA on User" in payload
        assert "fragment CircFragB on User" in payload
        assert "...CircFragB" in payload
        assert "...CircFragA" in payload

    def test_query_body_spreads_fragment(self):
        mat = self._materializer()
        payload, _ = mat.get_payload("getUser", _make_objects_bucket(), graphql_type="Query")
        assert "getUser" in payload
        # The operation body should use one of the circular fragments
        assert "CircFragA" in payload

    def test_scalar_output_fallback(self):
        """When the output is a scalar type (no OBJECT) it should still produce a payload."""
        api = _make_api(
            query_output={"kind": "SCALAR", "name": "String", "ofType": None, "type": "String"},
            objects={},
        )
        mat = DOSCircularFragmentMaterializer(api=api, fail_on_hard_dependency_not_met=False)
        try:
            payload, _ = mat.get_payload("getUser", _make_objects_bucket(), graphql_type="Query")
            assert "getUser" in payload
        except Exception as exc:
            self.fail(f"get_payload raised unexpectedly: {exc}")

    def test_raises_on_invalid_graphql_type(self):
        mat = self._materializer()
        with self.assertRaises(ValueError):
            mat.get_payload("getUser", _make_objects_bucket(), graphql_type="Subscription")


# ---------------------------------------------------------------------------
# DOSResourceExhaustionMaterializer / ResourceExhaustionGetter
# ---------------------------------------------------------------------------

class TestResourceExhaustionGetter(unittest.TestCase):

    def setUp(self):
        self.getter = ResourceExhaustionGetter()

    def test_pagination_input_returns_large_value(self):
        for name in PAGINATION_INPUT_NAMES:
            self.assertEqual(
                self.getter.get_random_int(name),
                LARGE_PAGINATION_VALUE,
                f"Expected LARGE_PAGINATION_VALUE for input '{name}'",
            )

    def test_non_pagination_input_returns_normal_value(self):
        value = self.getter.get_random_int("price")
        self.assertNotEqual(value, LARGE_PAGINATION_VALUE)
        self.assertGreaterEqual(value, 0)

    def test_case_insensitive_matching(self):
        self.assertEqual(self.getter.get_random_int("LIMIT"), LARGE_PAGINATION_VALUE)
        self.assertEqual(self.getter.get_random_int("First"), LARGE_PAGINATION_VALUE)


class TestDOSResourceExhaustionMaterializer(unittest.TestCase):

    def _materializer(self, inputs=None):
        api = _make_api(inputs=inputs or {})
        return DOSResourceExhaustionMaterializer(api=api, fail_on_hard_dependency_not_met=False)

    def test_payload_basic_structure(self):
        mat = self._materializer()
        payload, _ = mat.get_payload("getUser", _make_objects_bucket(), graphql_type="Query")
        assert "getUser" in payload

    def test_large_value_injected_for_limit_input(self):
        limit_input = {
            "limit": {
                "kind": "SCALAR",
                "name": "limit",
                "ofType": None,
                "type": "Int",
            }
        }
        mat = self._materializer(inputs=limit_input)
        payload, _ = mat.get_payload("getUser", _make_objects_bucket(), graphql_type="Query")
        assert str(LARGE_PAGINATION_VALUE) in payload

    def test_raises_on_invalid_graphql_type(self):
        mat = self._materializer()
        with self.assertRaises(ValueError):
            mat.get_payload("getUser", _make_objects_bucket(), graphql_type="Subscription")


# ---------------------------------------------------------------------------
# DOSDetector base — _is_vulnerable / _is_potentially_vulnerable
# ---------------------------------------------------------------------------

def _make_dos_detector(detector_class):
    api = _make_api()
    node = MagicMock()
    node.name = "getUser"
    bucket = _make_objects_bucket()
    return detector_class(api=api, node=node, objects_bucket=bucket, graphql_type="Query")


def _mock_response(status_code: int, text: str = ""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


class TestDOSDetectorBase(unittest.TestCase):

    def _detector(self, klass=FieldDuplicationDetector):
        return _make_dos_detector(klass)

    def test_5xx_is_vulnerable(self):
        det = self._detector()
        self.assertTrue(det._is_vulnerable({}, _mock_response(500)))
        self.assertTrue(det._is_vulnerable({}, _mock_response(503)))

    def test_safe_rejection_pattern_is_not_vulnerable(self):
        det = self._detector(CircularFragmentDetector)
        for pattern in DOS_SAFE_REJECTION_PATTERNS:
            resp = _mock_response(200, text=pattern)
            self.assertFalse(
                det._is_vulnerable({}, resp),
                f"Expected not-vulnerable for safe rejection pattern '{pattern}'",
            )

    def test_timeout_error_in_body_is_vulnerable(self):
        det = self._detector()
        self.assertTrue(det._is_vulnerable({}, _mock_response(200, text="query timeout exceeded")))

    def test_complexity_error_in_body_is_vulnerable(self):
        det = self._detector()
        self.assertTrue(det._is_vulnerable({}, _mock_response(200, text="query complexity limit reached")))

    def test_429_is_potentially_vulnerable(self):
        det = self._detector()
        self.assertTrue(det._is_potentially_vulnerable({}, _mock_response(429)))

    def test_200_ok_is_not_vulnerable(self):
        det = self._detector()
        self.assertFalse(det._is_vulnerable({}, _mock_response(200, text='{"data": {"getUser": {"id": "1"}}}')))
        self.assertFalse(det._is_potentially_vulnerable({}, _mock_response(200)))

    def test_evidence_includes_status_code_for_5xx(self):
        det = self._detector()
        evidence = det._get_evidence({}, _mock_response(500))
        self.assertIn("500", evidence)

    def test_evidence_includes_matched_pattern(self):
        det = self._detector()
        evidence = det._get_evidence({}, _mock_response(200, text="timeout occurred"))
        self.assertIn("timeout", evidence)


# ---------------------------------------------------------------------------
# Detector DETECTION_NAME and materializer wiring
# ---------------------------------------------------------------------------

class TestDetectorRegistration(unittest.TestCase):

    def test_field_duplication_detector_name(self):
        det = _make_dos_detector(FieldDuplicationDetector)
        self.assertIn("Field Duplication", det.DETECTION_NAME)

    def test_circular_fragment_detector_name(self):
        det = _make_dos_detector(CircularFragmentDetector)
        self.assertIn("Circular Fragment", det.DETECTION_NAME)

    def test_resource_exhaustion_detector_name(self):
        det = _make_dos_detector(ResourceExhaustionDetector)
        self.assertIn("Resource Exhaustion", det.DETECTION_NAME)

    def test_field_duplication_uses_correct_materializer(self):
        det = _make_dos_detector(FieldDuplicationDetector)
        self.assertIs(det.materializer, DOSFieldDuplicationMaterializer)

    def test_circular_fragment_uses_correct_materializer(self):
        det = _make_dos_detector(CircularFragmentDetector)
        self.assertIs(det.materializer, DOSCircularFragmentMaterializer)

    def test_resource_exhaustion_uses_correct_materializer(self):
        det = _make_dos_detector(ResourceExhaustionDetector)
        self.assertIs(det.materializer, DOSResourceExhaustionMaterializer)


if __name__ == "__main__":
    unittest.main()
