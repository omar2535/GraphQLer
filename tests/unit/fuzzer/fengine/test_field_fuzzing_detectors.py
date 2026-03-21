import unittest
from unittest.mock import MagicMock, patch

from graphqler import config
from graphqler.fuzzer.engine.detectors.field_fuzzing.field_charset_fuzzing_detector import (
    FieldCharsetFuzzingDetector,
    collect_string_inputs,
    _resolve_scalar_type,
)
from graphqler.fuzzer.engine.detectors.field_fuzzing.id_enumeration_detector import (
    IDEnumerationDetector,
    collect_id_inputs,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_api(inputs: dict, graphql_type: str = "Query", node_name: str = "searchItems"):
    api = MagicMock()
    api.url = "http://localhost/graphql"
    if graphql_type == "Query":
        api.queries = {node_name: {"inputs": inputs, "hardDependsOn": {}, "softDependsOn": {}}}
        api.mutations = {}
    else:
        api.queries = {}
        api.mutations = {node_name: {"inputs": inputs, "hardDependsOn": {}, "softDependsOn": {}}}
    return api


def _make_detector(detector_class, inputs: dict, graphql_type: str = "Query", node_name: str = "searchItems"):
    api = _make_api(inputs, graphql_type, node_name)
    node = MagicMock()
    node.name = node_name
    objects_bucket = MagicMock()
    objects_bucket.is_object_in_bucket.return_value = False
    return detector_class(api=api, node=node, objects_bucket=objects_bucket, graphql_type=graphql_type)


STRING_INPUT = {
    "filter": {
        "kind": "NON_NULL",
        "name": "filter",
        "ofType": {"kind": "SCALAR", "name": "String", "ofType": None, "type": "String"},
        "type": None,
    }
}

INT_INPUT = {
    "id": {
        "kind": "NON_NULL",
        "name": "id",
        "ofType": {"kind": "SCALAR", "name": "Int", "ofType": None, "type": "Int"},
        "type": None,
    }
}

ID_INPUT = {
    "userId": {
        "kind": "SCALAR",
        "name": "ID",
        "ofType": None,
        "type": "ID",
    }
}


# ── _resolve_scalar_type ──────────────────────────────────────────────────────

class TestResolveScalarType(unittest.TestCase):
    def test_direct_scalar(self):
        self.assertEqual(_resolve_scalar_type({"kind": "SCALAR", "type": "String", "ofType": None}), "String")

    def test_non_null_wrapping(self):
        field = {"kind": "NON_NULL", "ofType": {"kind": "SCALAR", "type": "Int", "ofType": None}}
        self.assertEqual(_resolve_scalar_type(field), "Int")

    def test_double_wrapped(self):
        field = {"kind": "NON_NULL", "ofType": {"kind": "NON_NULL", "ofType": {"kind": "SCALAR", "type": "ID", "ofType": None}}}
        self.assertEqual(_resolve_scalar_type(field), "ID")

    def test_object_returns_none(self):
        field = {"kind": "OBJECT", "type": "User", "ofType": None}
        self.assertIsNone(_resolve_scalar_type(field))

    def test_none_input(self):
        self.assertIsNone(_resolve_scalar_type(None))


# ── collect_string_inputs ─────────────────────────────────────────────────────

class TestCollectStringInputs(unittest.TestCase):
    def test_finds_string_field(self):
        self.assertIn("filter", collect_string_inputs(STRING_INPUT))

    def test_ignores_int_field(self):
        self.assertEqual(collect_string_inputs(INT_INPUT), [])

    def test_mixed_inputs(self):
        mixed = {**STRING_INPUT, **INT_INPUT}
        result = collect_string_inputs(mixed)
        self.assertIn("filter", result)
        self.assertNotIn("id", result)


# ── collect_id_inputs ─────────────────────────────────────────────────────────

class TestCollectIdInputs(unittest.TestCase):
    def test_finds_int_field(self):
        self.assertIn("id", collect_id_inputs(INT_INPUT))

    def test_finds_id_field(self):
        self.assertIn("userId", collect_id_inputs(ID_INPUT))

    def test_ignores_string_field(self):
        self.assertEqual(collect_id_inputs(STRING_INPUT), [])


# ── FieldCharsetFuzzingDetector ───────────────────────────────────────────────

class TestFieldCharsetFuzzingDetector(unittest.TestCase):
    def setUp(self):
        self._orig_skip = config.SKIP_ENUMERATION_ATTACKS
        self._orig_charset = config.FIELD_CHARSET
        self._orig_max = config.MAX_CHARSET_FUZZ_FIELDS
        self._orig_threshold = config.FIELD_RESPONSE_LENGTH_VARIANCE_THRESHOLD
        config.SKIP_ENUMERATION_ATTACKS = False
        config.FIELD_CHARSET = "abc"         # tiny charset for test speed
        config.MAX_CHARSET_FUZZ_FIELDS = 1
        config.FIELD_RESPONSE_LENGTH_VARIANCE_THRESHOLD = 0.1

    def tearDown(self):
        config.SKIP_ENUMERATION_ATTACKS = self._orig_skip
        config.FIELD_CHARSET = self._orig_charset
        config.MAX_CHARSET_FUZZ_FIELDS = self._orig_max
        config.FIELD_RESPONSE_LENGTH_VARIANCE_THRESHOLD = self._orig_threshold

    def test_skips_when_disabled(self):
        config.SKIP_ENUMERATION_ATTACKS = True
        det = _make_detector(FieldCharsetFuzzingDetector, STRING_INPUT)
        confirmed, potential = det.detect()
        self.assertFalse(confirmed)
        self.assertFalse(potential)

    def test_skips_when_no_string_inputs(self):
        config.SKIP_ENUMERATION_ATTACKS = False
        det = _make_detector(FieldCharsetFuzzingDetector, INT_INPUT)
        confirmed, potential = det.detect()
        self.assertFalse(confirmed)
        self.assertFalse(potential)

    @patch("graphqler.fuzzer.engine.detectors.field_fuzzing.field_charset_fuzzing_detector.Stats")
    @patch("graphqler.fuzzer.engine.detectors.field_fuzzing.field_charset_fuzzing_detector.plugins_handler")
    def test_flags_potential_on_high_variance(self, mock_ph, mock_stats):
        mock_stats.return_value = MagicMock()
        # 'a' → short response, 'b' → very long, 'c' → short
        def fake_send(url, payload):
            resp = MagicMock()
            if '"a"' in payload:
                resp.text = "x" * 100
                resp.status_code = 200
            elif '"b"' in payload:
                resp.text = "x" * 2000   # big outlier
                resp.status_code = 200
            else:
                resp.text = "x" * 100
                resp.status_code = 200
            return ({}, resp)

        mock_ph.get_request_utils.return_value.send_graphql_request.side_effect = fake_send

        det = _make_detector(FieldCharsetFuzzingDetector, STRING_INPUT)
        # patch _build_payload to return non-empty string
        det._build_payload = lambda field, val: f'{{ searchItems(filter: "{val}") {{ id }} }}'

        confirmed, potential = det.detect()
        self.assertFalse(confirmed, "charset fuzzing should never confirm")
        self.assertTrue(potential, "high response variance should flag as potential")

    @patch("graphqler.fuzzer.engine.detectors.field_fuzzing.field_charset_fuzzing_detector.Stats")
    @patch("graphqler.fuzzer.engine.detectors.field_fuzzing.field_charset_fuzzing_detector.plugins_handler")
    def test_no_flag_on_uniform_responses(self, mock_ph, mock_stats):
        mock_stats.return_value = MagicMock()
        def fake_send(url, payload):
            resp = MagicMock()
            resp.text = "x" * 150
            resp.status_code = 200
            return ({}, resp)

        mock_ph.get_request_utils.return_value.send_graphql_request.side_effect = fake_send
        det = _make_detector(FieldCharsetFuzzingDetector, STRING_INPUT)
        det._build_payload = lambda field, val: f'{{ searchItems(filter: "{val}") {{ id }} }}'

        _, potential = det.detect()
        self.assertFalse(potential, "uniform response lengths should NOT flag")


# ── IDEnumerationDetector ─────────────────────────────────────────────────────

class TestIDEnumerationDetector(unittest.TestCase):
    def setUp(self):
        self._orig_skip = config.SKIP_ENUMERATION_ATTACKS
        self._orig_count = config.ID_ENUMERATION_COUNT
        self._orig_threshold = config.ID_ENUMERATION_SUCCESS_THRESHOLD
        config.SKIP_ENUMERATION_ATTACKS = False
        config.ID_ENUMERATION_COUNT = 5
        config.ID_ENUMERATION_SUCCESS_THRESHOLD = 2

    def tearDown(self):
        config.SKIP_ENUMERATION_ATTACKS = self._orig_skip
        config.ID_ENUMERATION_COUNT = self._orig_count
        config.ID_ENUMERATION_SUCCESS_THRESHOLD = self._orig_threshold

    def test_skips_when_disabled(self):
        config.SKIP_ENUMERATION_ATTACKS = True
        det = _make_detector(IDEnumerationDetector, INT_INPUT)
        confirmed, potential = det.detect()
        self.assertFalse(confirmed)
        self.assertFalse(potential)

    def test_skips_when_no_id_inputs(self):
        config.SKIP_ENUMERATION_ATTACKS = False
        det = _make_detector(IDEnumerationDetector, STRING_INPUT)
        confirmed, potential = det.detect()
        self.assertFalse(confirmed)
        self.assertFalse(potential)

    @patch("graphqler.fuzzer.engine.detectors.field_fuzzing.id_enumeration_detector.Stats")
    @patch("graphqler.fuzzer.engine.detectors.field_fuzzing.id_enumeration_detector.plugins_handler")
    def test_flags_potential_on_multiple_id_hits(self, mock_ph, mock_stats):
        mock_stats.return_value = MagicMock()
        # IDs 1, 2, 3 return data; 4, 5 do not
        def fake_send(url, payload):
            resp = MagicMock()
            resp.status_code = 200
            resp.text = "{}"
            for i in (1, 2, 3):
                if f'"{i}"' in payload or f': {i}' in payload:
                    return ({"data": {"searchItems": {"id": i, "name": f"item{i}"}}}, resp)
            return ({"data": {"searchItems": None}}, resp)

        mock_ph.get_request_utils.return_value.send_graphql_request.side_effect = fake_send

        det = _make_detector(IDEnumerationDetector, INT_INPUT)
        det._probe_ids = lambda f: (3, ['query { searchItems(id: 3) { id } }'])

        confirmed, potential = det.detect()
        self.assertFalse(confirmed, "ID enumeration should never confirm")
        self.assertTrue(potential, "3 IDs returning data >= threshold of 2 should flag")

    @patch("graphqler.fuzzer.engine.detectors.field_fuzzing.id_enumeration_detector.Stats")
    @patch("graphqler.fuzzer.engine.detectors.field_fuzzing.id_enumeration_detector.plugins_handler")
    def test_no_flag_when_single_id_returns_data(self, mock_ph, mock_stats):
        mock_stats.return_value = MagicMock()
        det = _make_detector(IDEnumerationDetector, INT_INPUT)
        det._probe_ids = lambda f: (1, ['query { searchItems(id: 1) { id } }'])

        _, potential = det.detect()
        self.assertFalse(potential, "only 1 ID hit < threshold of 2 should NOT flag")

    @patch("graphqler.fuzzer.engine.detectors.field_fuzzing.id_enumeration_detector.Stats")
    @patch("graphqler.fuzzer.engine.detectors.field_fuzzing.id_enumeration_detector.plugins_handler")
    def test_no_flag_when_no_ids_return_data(self, mock_ph, mock_stats):
        mock_stats.return_value = MagicMock()
        det = _make_detector(IDEnumerationDetector, INT_INPUT)
        det._probe_ids = lambda f: (0, [])

        _, potential = det.detect()
        self.assertFalse(potential, "0 ID hits should NOT flag")
