import unittest
from unittest.mock import MagicMock, patch

from graphqler.fuzzer.engine.detectors.nosql_injection.blind_nosql_extractor import (
    BlindNoSQLExtractor,
    _make_regex_payload,
    _has_data,
)
from graphqler import config


# ---------------------------------------------------------------------------
# Helper payload fixture
# ---------------------------------------------------------------------------
SAMPLE_PAYLOAD = (
    'query {\n'
    '  doctors(search: "{$gt: \\"\\"}" ) {\n'
    '    id\n'
    '    firstName\n'
    '  }\n'
    '}'
)


class TestMakeRegexPayload(unittest.TestCase):
    """Unit tests for the payload substitution helper."""

    def test_replaces_known_operator(self):
        result = _make_regex_payload(SAMPLE_PAYLOAD, "4f")
        self.assertIn('$regex', result)
        self.assertIn("^4f", result)
        self.assertNotIn("{$gt", result)

    def test_no_known_operator_returns_unchanged(self):
        plain = 'query { doctors(search: "hello") { id } }'
        result = _make_regex_payload(plain, "4f")
        self.assertEqual(result, plain)

    def test_empty_prefix(self):
        result = _make_regex_payload(SAMPLE_PAYLOAD, "")
        self.assertIn('$regex', result)
        self.assertNotIn("{$gt", result)


class TestHasData(unittest.TestCase):
    """Unit tests for the boolean oracle helper."""

    def test_non_empty_list_value(self):
        self.assertTrue(_has_data({"data": {"doctors": [{"id": "1"}]}}))

    def test_non_empty_dict_value(self):
        self.assertTrue(_has_data({"data": {"user": {"id": "1"}}}))

    def test_null_value(self):
        self.assertFalse(_has_data({"data": {"doctors": None}}))

    def test_empty_list(self):
        self.assertFalse(_has_data({"data": {"doctors": []}}))

    def test_empty_dict(self):
        self.assertFalse(_has_data({"data": {"doctors": {}}}))

    def test_none_response(self):
        self.assertFalse(_has_data(None))

    def test_missing_data_key(self):
        self.assertFalse(_has_data({"errors": [{"message": "oops"}]}))


class TestBlindNoSQLExtractor(unittest.TestCase):
    """Unit tests for BlindNoSQLExtractor using a mocked request utility."""

    def setUp(self):
        # Enable blind extraction for tests
        self._orig_flag = config.NOSQLI_BLIND_EXTRACTION
        self._orig_charset = config.NOSQLI_EXTRACTION_CHARSET
        self._orig_max = config.NOSQLI_MAX_EXTRACTION_LENGTH
        config.NOSQLI_BLIND_EXTRACTION = True
        config.NOSQLI_EXTRACTION_CHARSET = "0123456789abcdef-"
        config.NOSQLI_MAX_EXTRACTION_LENGTH = 64

    def tearDown(self):
        config.NOSQLI_BLIND_EXTRACTION = self._orig_flag
        config.NOSQLI_EXTRACTION_CHARSET = self._orig_charset
        config.NOSQLI_MAX_EXTRACTION_LENGTH = self._orig_max

    def _make_oracle(self, secret: str):
        """Return a mock send_graphql_request that returns data iff the injected
        prefix is a real prefix of *secret*."""
        def oracle(url, payload):
            # Extract the prefix between ^ and the closing escaped quote \"
            import re
            m = re.search(r'\^(.*?)\\"', payload)
            if not m:
                return ({}, MagicMock(status_code=200))
            prefix = m.group(1)
            if secret.startswith(prefix) and prefix:
                return ({"data": {"doctors": [{"id": "x"}]}}, MagicMock(status_code=200))
            return ({"data": {"doctors": []}}, MagicMock(status_code=200))
        return oracle

    @patch("graphqler.fuzzer.engine.detectors.nosql_injection.blind_nosql_extractor.plugins_handler")
    def test_extracts_known_secret(self, mock_plugins):
        secret = "4f53"
        mock_plugins.get_request_utils.return_value.send_graphql_request.side_effect = self._make_oracle(secret)
        extractor = BlindNoSQLExtractor("http://localhost/graphql", SAMPLE_PAYLOAD)
        result = extractor.extract()
        self.assertEqual(result, secret)

    @patch("graphqler.fuzzer.engine.detectors.nosql_injection.blind_nosql_extractor.plugins_handler")
    def test_returns_empty_when_no_match(self, mock_plugins):
        # Server always returns empty data
        mock_plugins.get_request_utils.return_value.send_graphql_request.return_value = (
            {"data": {"doctors": []}}, MagicMock(status_code=200)
        )
        extractor = BlindNoSQLExtractor("http://localhost/graphql", SAMPLE_PAYLOAD)
        result = extractor.extract()
        self.assertEqual(result, "")

    @patch("graphqler.fuzzer.engine.detectors.nosql_injection.blind_nosql_extractor.plugins_handler")
    def test_respects_max_length(self, mock_plugins):
        config.NOSQLI_MAX_EXTRACTION_LENGTH = 3
        # Server always says the first char '0' matches (so it would loop forever without cap)
        def always_match(url, payload):
            import re
            m = re.search(r'\^(.*?)\\"', payload)
            prefix = m.group(1) if m else ""
            if "000"[:len(prefix)] == prefix and prefix:
                return ({"data": {"doctors": [{"id": "1"}]}}, MagicMock(status_code=200))
            return ({"data": {"doctors": []}}, MagicMock(status_code=200))
        mock_plugins.get_request_utils.return_value.send_graphql_request.side_effect = always_match
        extractor = BlindNoSQLExtractor("http://localhost/graphql", SAMPLE_PAYLOAD)
        result = extractor.extract()
        self.assertLessEqual(len(result), 3)

    @patch("graphqler.fuzzer.engine.detectors.nosql_injection.blind_nosql_extractor.plugins_handler")
    def test_disabled_flag_returns_empty(self, mock_plugins):
        config.NOSQLI_BLIND_EXTRACTION = False
        mock_plugins.get_request_utils.return_value.send_graphql_request.return_value = (
            {"data": {"doctors": [{"id": "x"}]}}, MagicMock(status_code=200)
        )
        extractor = BlindNoSQLExtractor("http://localhost/graphql", SAMPLE_PAYLOAD)
        result = extractor.extract()
        self.assertEqual(result, "")
        # No requests should have been sent
        mock_plugins.get_request_utils.return_value.send_graphql_request.assert_not_called()

    @patch("graphqler.fuzzer.engine.detectors.nosql_injection.blind_nosql_extractor.plugins_handler")
    def test_no_operator_in_payload_returns_empty(self, mock_plugins):
        plain_payload = 'query { doctors(search: "hello") { id } }'
        extractor = BlindNoSQLExtractor("http://localhost/graphql", plain_payload)
        result = extractor.extract()
        self.assertEqual(result, "")
        mock_plugins.get_request_utils.return_value.send_graphql_request.assert_not_called()
