import unittest
from unittest.mock import MagicMock, patch
import time

from graphqler.fuzzer.engine.detectors.time_sql_injection.time_sql_injection_materializer import (
    TimeSQLInjectionGetter,
    _build_payloads,
)
from graphqler.fuzzer.engine.detectors.time_sql_injection.time_sql_injection_detector import (
    TimeSQLInjectionDetector,
)
from graphqler import config


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_detector(elapsed: float, baseline: float = 0.0):
    """Return a configured TimeSQLInjectionDetector with pre-set timing attributes."""
    api = MagicMock()
    api.url = "http://localhost/graphql"
    node = MagicMock()
    node.name = "searchUser"
    objects_bucket = MagicMock()

    detector = TimeSQLInjectionDetector(api=api, node=node, objects_bucket=objects_bucket, graphql_type="Query")
    detector.elapsed_time = elapsed
    detector.baseline_time = baseline
    detector.time_delta = max(0.0, elapsed - baseline)
    detector.payload = "{ searchUser(username: \"1' AND SLEEP(3)--\") { id } }"
    return detector


# ---------------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------------

class TestBuildPayloads(unittest.TestCase):
    def test_generates_four_payloads(self):
        payloads = _build_payloads(3)
        self.assertEqual(len(payloads), 4)

    def test_sleep_seconds_parameterised(self):
        payloads = _build_payloads(5)
        self.assertTrue(any("5" in p for p in payloads))
        payloads2 = _build_payloads(3)
        self.assertTrue(any("3" in p for p in payloads2))

    def test_covers_mysql_postgresql_mssql(self):
        payloads = _build_payloads(3)
        joined = " ".join(payloads).lower()
        self.assertIn("sleep", joined)
        self.assertIn("pg_sleep", joined)
        self.assertIn("waitfor", joined)


# ---------------------------------------------------------------------------
# Getter rotation
# ---------------------------------------------------------------------------

class TestTimeSQLInjectionGetter(unittest.TestCase):
    def test_rotates_through_payloads(self):
        getter = TimeSQLInjectionGetter(sleep_seconds=3)
        results = {getter.get_random_string("username") for _ in range(4)}
        self.assertGreater(len(results), 1, "Expected payload rotation across 4 calls")

    def test_non_sensitive_field_returns_default(self):
        getter = TimeSQLInjectionGetter(sleep_seconds=3)
        result = getter.get_random_string("randomFieldXyz")
        # Should fall back to the parent Getter (returns some non-empty string)
        self.assertIsInstance(result, str)
        # Must not be a sleep payload
        self.assertNotIn("SLEEP", result)
        self.assertNotIn("pg_sleep", result)
        self.assertNotIn("WAITFOR", result)


# ---------------------------------------------------------------------------
# Detector vulnerability assessment
# ---------------------------------------------------------------------------

class TestTimeSQLInjectionDetector(unittest.TestCase):
    def setUp(self):
        self._orig_sleep = config.TIME_BASED_SQL_SLEEP_SECONDS
        self._orig_ratio = config.TIME_BASED_SQL_THRESHOLD_RATIO
        config.TIME_BASED_SQL_SLEEP_SECONDS = 3
        config.TIME_BASED_SQL_THRESHOLD_RATIO = 0.8  # threshold = 2.4s

    def tearDown(self):
        config.TIME_BASED_SQL_SLEEP_SECONDS = self._orig_sleep
        config.TIME_BASED_SQL_THRESHOLD_RATIO = self._orig_ratio

    # --- _is_vulnerable ---

    def test_confirmed_when_elapsed_exceeds_threshold(self):
        det = _make_detector(elapsed=2.5)  # > 2.4 threshold
        self.assertTrue(det._is_vulnerable(None, MagicMock()))

    def test_not_confirmed_when_elapsed_below_threshold(self):
        det = _make_detector(elapsed=0.5)
        self.assertFalse(det._is_vulnerable(None, MagicMock()))

    def test_threshold_boundary_equal(self):
        det = _make_detector(elapsed=2.41)  # just above 3 * 0.8 (=2.4000...04 in float)
        self.assertTrue(det._is_vulnerable(None, MagicMock()))

    # --- _is_potentially_vulnerable ---

    def test_potentially_vulnerable_between_1s_and_threshold(self):
        det = _make_detector(elapsed=1.5)
        self.assertTrue(det._is_potentially_vulnerable(None, MagicMock()))

    def test_not_potentially_vulnerable_when_fast(self):
        det = _make_detector(elapsed=0.3)
        self.assertFalse(det._is_potentially_vulnerable(None, MagicMock()))

    def test_not_potentially_vulnerable_when_already_confirmed(self):
        # Confirmed → _is_potentially_vulnerable should return False (not double-count)
        det = _make_detector(elapsed=3.0)
        self.assertFalse(det._is_potentially_vulnerable(None, MagicMock()))

    # --- _get_evidence ---

    def test_evidence_contains_elapsed_when_confirmed(self):
        det = _make_detector(elapsed=3.1, baseline=0.0)
        evidence = det._get_evidence(None, MagicMock())
        self.assertIn("3.10s", evidence)
        self.assertIn("threshold", evidence)

    def test_evidence_describes_slow_response_when_potential(self):
        det = _make_detector(elapsed=1.8, baseline=0.0)
        evidence = det._get_evidence(None, MagicMock())
        self.assertIn("1.80s", evidence)
        self.assertIn("below confirmed threshold", evidence)

    def test_evidence_empty_when_fast(self):
        det = _make_detector(elapsed=0.2, baseline=0.0)
        evidence = det._get_evidence(None, MagicMock())
        self.assertEqual(evidence, "")

    # --- full detect() with mocked request ---

    @patch("graphqler.fuzzer.engine.detectors.time_sql_injection.time_sql_injection_detector.plugins_handler")
    @patch("graphqler.fuzzer.engine.detectors.time_sql_injection.time_sql_injection_detector.Stats")
    def test_detect_flags_confirmed_on_slow_response(self, mock_stats, mock_plugins):
        api = MagicMock()
        api.url = "http://localhost/graphql"
        node = MagicMock()
        node.name = "searchUser"
        objects_bucket = MagicMock()

        fast_response = MagicMock()
        fast_response.status_code = 200
        fast_response.text = '{"data": {"searchUser": null}}'

        def slow_request(url, payload):
            time.sleep(0.05)  # tiny sleep — we'll patch monotonic instead
            return ({"data": {"searchUser": None}}, fast_response)

        mock_plugins.get_request_utils.return_value.send_graphql_request.side_effect = slow_request
        mock_stats.return_value = MagicMock()

        detector = TimeSQLInjectionDetector(api=api, node=node, objects_bucket=objects_bucket, graphql_type="Query")

        # Patch time.monotonic to simulate: fast baseline (0.1s), slow injection (3.1s)
        # 4 calls total: baseline_start, baseline_end, injection_start, injection_end
        timestamps = [1000.0, 1000.1, 1000.1, 1003.1]
        call_count = [0]
        def fake_monotonic():
            val = timestamps[min(call_count[0], len(timestamps) - 1)]
            call_count[0] += 1
            return val
        with patch("graphqler.fuzzer.engine.detectors.time_sql_injection.time_sql_injection_detector.time.monotonic", side_effect=fake_monotonic):
            confirmed, potential = detector.detect()

        self.assertTrue(confirmed)
        self.assertFalse(potential)
