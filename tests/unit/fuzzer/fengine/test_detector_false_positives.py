"""False-positive regression tests for injection detectors.

Each test validates that a benign-but-realistic API response does NOT
trigger a vulnerability flag.  These were identified as sources of false
positives before the fixes in this PR.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from graphqler.graph.node import Node


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_response(status: int = 200, text: str = '{"data":{"searchItems":{"id":1}}}') -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    return resp


def _make_gql(data: dict | None = None, errors: list | None = None) -> dict:
    result: dict = {}
    if data is not None:
        result["data"] = data
    if errors is not None:
        result["errors"] = errors
    return result


def _make_api(node_name: str = "searchItems") -> MagicMock:
    api = MagicMock()
    api.url = "http://fake/graphql"
    api.queries = {node_name: {"inputs": {}, "output": {}}}
    api.mutations = {}
    api.objects = {}
    return api


def _make_node(name: str = "searchItems") -> Node:
    return Node(graphql_type="Query", name=name, body={})


# ── SQL Injection — false positive: data returned without any error ───────────

class TestSQLInjectionFalsePositive(unittest.TestCase):
    """The old blind check fired whenever HTTP 200 + data was returned with an
    injection payload.  Parameterised queries do exactly this — always return
    data safely.  After the fix, _is_potentially_vulnerable() must return False."""

    def _make_detector(self):
        from graphqler.fuzzer.engine.detectors.sql_injection.sql_injection_detector import SQLInjectionDetector
        det = SQLInjectionDetector(
            api=_make_api(), node=_make_node(), objects_bucket=MagicMock(), graphql_type="Query"
        )
        det.payload = "{ searchItems(name: \"' OR 1=1--\") { id name } }"
        return det

    def test_no_flag_when_200_data_but_no_error_pattern(self):
        """Parameterised endpoint returns data on injection payload — must NOT flag."""
        det = self._make_detector()
        gql = _make_gql(data={"searchItems": {"id": 1, "name": "test"}})
        http = _make_response(200, '{"data":{"searchItems":{"id":1,"name":"test"}}}')
        self.assertFalse(det._is_potentially_vulnerable(gql, http))

    def test_no_flag_when_list_data_returned(self):
        """Parameterised query returning a list of records must NOT flag."""
        det = self._make_detector()
        gql = _make_gql(data={"searchItems": [{"id": 1}, {"id": 2}]})
        http = _make_response(200, '{"data":{"searchItems":[{"id":1},{"id":2}]}}')
        self.assertFalse(det._is_potentially_vulnerable(gql, http))

    def test_no_flag_when_null_data(self):
        det = self._make_detector()
        gql = _make_gql(data=None)
        http = _make_response(200, '{"data":null}')
        self.assertFalse(det._is_potentially_vulnerable(gql, http))

    def test_confirmed_flag_when_error_pattern_present(self):
        """Actual SQL error message should still trigger confirmed detection."""
        det = self._make_detector()
        http = _make_response(500, 'you have an error in your sql syntax near "OR"')
        self.assertTrue(det._is_vulnerable(_make_gql(), http))


# ── NoSQL Injection — false positive: both baseline and injection return data ─

class TestNoSQLInjectionFalsePositive(unittest.TestCase):
    """The old check fired when injection returned data — but if the benign
    baseline also returns data, we cannot infer a bypass occurred."""

    def _make_detector(self, baseline_has_data: bool = True):
        from graphqler.fuzzer.engine.detectors.nosql_injection.nosql_injection_detector import (
            NoSQLInjectionDetector,
        )
        det = NoSQLInjectionDetector(
            api=_make_api(), node=_make_node(), objects_bucket=MagicMock(), graphql_type="Query"
        )
        det.payload = '{ searchItems(filter: "{$gt: \\"\\"}") { id } }'
        det.baseline_has_data = baseline_has_data
        return det

    def test_no_flag_when_baseline_also_has_data(self):
        """API returns data regardless of input — operator did NOT bypass anything."""
        det = self._make_detector(baseline_has_data=True)
        gql = _make_gql(data={"searchItems": {"id": 1}})
        http = _make_response(200)
        self.assertFalse(det._is_potentially_vulnerable(gql, http))

    def test_no_flag_when_injection_returns_no_data(self):
        """Operator payload rejected (returns null) — not a bypass."""
        det = self._make_detector(baseline_has_data=False)
        gql = _make_gql(data={"searchItems": None})
        http = _make_response(200)
        self.assertFalse(det._is_potentially_vulnerable(gql, http))

    def test_flag_when_baseline_empty_injection_has_data(self):
        """Operator payload returned data when benign baseline returned none — real bypass signal."""
        det = self._make_detector(baseline_has_data=False)
        gql = _make_gql(data={"searchItems": {"id": 1, "username": "admin"}})
        http = _make_response(200)
        self.assertTrue(det._is_potentially_vulnerable(gql, http))

    def test_confirmed_flag_when_error_pattern_present(self):
        """Actual MongoDB error message should still trigger confirmed detection."""
        det = self._make_detector()
        http = _make_response(500, '{"error": "MongoError: bad query operator"}')
        self.assertTrue(det._is_vulnerable(_make_gql(), http))


# ── HTML Injection — false positive: 200+data but no reflection ──────────────

class TestHTMLInjectionFalsePositive(unittest.TestCase):
    """The old check fired whenever HTTP 200 + data was present — regardless of
    whether the HTML payload was reflected in the response body."""

    def _make_detector(self):
        from graphqler.fuzzer.engine.detectors.html_injection.html_injection_detector import HTMLInjectionDetector
        det = HTMLInjectionDetector(
            api=_make_api(), node=_make_node(), objects_bucket=MagicMock(), graphql_type="Query"
        )
        det.payload = '{ searchItems(name: "<h1>Hello world!</h1>") { id } }'
        return det

    def test_no_flag_when_200_data_but_no_reflection(self):
        """API stores/ignores the HTML and returns safe data — must NOT flag."""
        det = self._make_detector()
        gql = _make_gql(data={"searchItems": {"id": 1, "name": "stored safely"}})
        http = _make_response(200, '{"data":{"searchItems":{"id":1,"name":"stored safely"}}}')
        self.assertFalse(det._is_potentially_vulnerable(gql, http))

    def test_no_flag_when_payload_in_request_only(self):
        """The payload string is in the *request* body, not the response — must NOT flag."""
        det = self._make_detector()
        gql = _make_gql(data={"searchItems": None})
        http = _make_response(200, '{"data":{"searchItems":null}}')
        self.assertFalse(det._is_potentially_vulnerable(gql, http))

    def test_flag_when_html_reflected_in_response(self):
        """Server echoes the HTML back — definite reflection."""
        det = self._make_detector()
        gql = _make_gql(data={"searchItems": {"id": 1, "name": "<h1>Hello world!</h1>"}})
        http = _make_response(200, '{"data":{"searchItems":{"id":1,"name":"<h1>Hello world!</h1>"}}}')
        self.assertTrue(det._is_potentially_vulnerable(gql, http))

    def test_detection_name_is_html_injection(self):
        """Name was incorrectly 'Path Injection' before fix."""
        from graphqler.fuzzer.engine.detectors.html_injection.html_injection_detector import HTMLInjectionDetector
        det = HTMLInjectionDetector(
            api=_make_api(), node=_make_node(), objects_bucket=MagicMock(), graphql_type="Query"
        )
        self.assertEqual(det.DETECTION_NAME, "HTML Injection")


# ── Time-based SQL — false positive: slow but equally slow baseline ───────────

class TestTimeSQLInjectionFalsePositive(unittest.TestCase):
    """The old check used absolute elapsed time — a naturally slow endpoint
    (e.g., one calling an external API) would always fire.  After the fix,
    the *delta* over a benign baseline is used instead."""

    def _make_detector(self, elapsed: float, baseline: float):
        from graphqler.fuzzer.engine.detectors.time_sql_injection.time_sql_injection_detector import (
            TimeSQLInjectionDetector,
        )
        det = TimeSQLInjectionDetector(
            api=_make_api(), node=_make_node(), objects_bucket=MagicMock(), graphql_type="Query"
        )
        det.elapsed_time = elapsed
        det.baseline_time = baseline
        det.time_delta = max(0.0, elapsed - baseline)
        det.payload = '{ searchItems(name: "1\' AND SLEEP(3)--") { id } }'
        return det

    def test_no_flag_when_baseline_equally_slow(self):
        """Endpoint is slow (3 s) but so is the baseline — no injection signal."""
        det = self._make_detector(elapsed=3.5, baseline=3.2)
        self.assertFalse(det._is_vulnerable(None, MagicMock()))
        self.assertFalse(det._is_potentially_vulnerable(None, MagicMock()))

    def test_no_flag_when_both_slow_above_1s_delta_threshold(self):
        """Both baseline and injection are ~4 s; delta < 1 s — must not flag potential."""
        det = self._make_detector(elapsed=4.1, baseline=3.5)
        # delta = 0.6 → below the 1.0 s potential threshold
        self.assertFalse(det._is_potentially_vulnerable(None, MagicMock()))

    def test_flag_confirmed_when_delta_exceeds_threshold(self):
        """Fast baseline + slow injection (delta >= 2.4 s) — real signal."""
        det = self._make_detector(elapsed=3.0, baseline=0.1)
        # delta = 2.9 >= 2.4 threshold
        self.assertTrue(det._is_vulnerable(None, MagicMock()))

    def test_flag_potential_when_delta_between_1s_and_threshold(self):
        """Delta of 1.5 s qualifies as potentially vulnerable."""
        det = self._make_detector(elapsed=1.7, baseline=0.2)
        # delta = 1.5 >= 1.0 but < 2.4
        self.assertFalse(det._is_vulnerable(None, MagicMock()))
        self.assertTrue(det._is_potentially_vulnerable(None, MagicMock()))

    def test_evidence_reports_baseline_and_delta(self):
        """Evidence string should include both baseline and delta for triage."""
        det = self._make_detector(elapsed=3.5, baseline=0.2)
        evidence = det._get_evidence(None, MagicMock())
        self.assertIn("baseline", evidence)


# ── Field Charset Fuzzing — false positive: uniform lengths ──────────────────

class TestCharsetFuzzingFalsePositive(unittest.TestCase):
    """The old threshold (0.2) fired when response lengths varied only slightly —
    a normal search API returning different result counts would trigger.  After
    the fix, the detector also requires near-empty responses for some chars."""

    def _make_detector(self):
        from graphqler.fuzzer.engine.detectors.field_fuzzing.field_charset_fuzzing_detector import (
            FieldCharsetFuzzingDetector,
        )
        api = _make_api()
        api.queries = {"searchItems": {"inputs": {"query": {"kind": "SCALAR", "name": "query", "type": "String", "ofType": None}}, "output": {}}}
        det = FieldCharsetFuzzingDetector(
            api=api, node=_make_node(), objects_bucket=MagicMock(), graphql_type="Query"
        )
        return det

    def test_no_flag_when_all_lengths_similar(self):
        """All characters produce the same length — no oracle signal."""
        det = self._make_detector()
        with patch.object(det, "_get_response_length", return_value=500):
            self.assertFalse(det._field_shows_variance("query"))

    def test_no_flag_when_lengths_vary_but_none_near_zero(self):
        """Lengths vary (search returns different counts) but no near-empty responses.
        This is a classic false positive pattern for search APIs."""
        det = self._make_detector()
        # Simulate search: 'a' returns lots of records, 'z' returns few, none empty
        lengths = [5000] * 5 + [3000] * 10 + [1500] * 10 + [800] * 11
        call_count = [0]

        def side_effect(field, char):
            i = call_count[0] % len(lengths)
            call_count[0] += 1
            return lengths[i]

        with patch.object(det, "_get_response_length", side_effect=side_effect):
            self.assertFalse(det._field_shows_variance("query"))

    def test_flag_when_some_chars_produce_near_empty_responses(self):
        """Oracle: specific chars return data (large), others return nothing (tiny).
        This is the classic blind injection pattern — should flag."""
        det = self._make_detector()
        # 2 chars match (large response), rest return near-empty error
        import graphqler.config as cfg
        n_chars = len(cfg.FIELD_CHARSET)
        lengths: list[int] = []
        for i in range(n_chars):
            lengths.append(5000 if i < 2 else 50)  # first 2 match, rest don't

        call_count = [0]

        def side_effect(field, char):
            i = call_count[0]
            call_count[0] += 1
            return lengths[i] if i < len(lengths) else 50

        with patch.object(det, "_get_response_length", side_effect=side_effect):
            self.assertTrue(det._field_shows_variance("query"))
