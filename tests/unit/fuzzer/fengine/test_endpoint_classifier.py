"""Unit tests for EndpointPrivacyClassifier and IDEnumerationDetector scope guard."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from graphqler.fuzzer.engine.detectors.field_fuzzing.endpoint_classifier import (
    EndpointPrivacyClassifier,
    _heuristic_score,
    _split_name,
)


# ── _split_name ───────────────────────────────────────────────────────────────

class TestSplitName:
    def test_camel_case(self):
        assert _split_name("getUserProfile") == ["get", "user", "profile"]

    def test_pascal_case(self):
        assert _split_name("UserProfile") == ["user", "profile"]

    def test_snake_case(self):
        assert _split_name("get_user_order") == ["get", "user", "order"]

    def test_single_word(self):
        assert _split_name("books") == ["books"]

    def test_consecutive_capitals(self):
        assert _split_name("getSSNValue") == ["get", "ssn", "value"]

    def test_empty(self):
        assert _split_name("") == []


# ── _heuristic_score ──────────────────────────────────────────────────────────

class TestHeuristicScore:
    def test_private_endpoint_name(self):
        score = _heuristic_score("getUserOrders", "Order", [])
        assert score >= 2, f"Expected private score, got {score}"

    def test_public_endpoint_name(self):
        score = _heuristic_score("getBooks", "Book", [])
        assert score <= -1, f"Expected public score, got {score}"

    def test_sensitive_field_boosts_score(self):
        base = _heuristic_score("getData", "Record", [])
        with_email = _heuristic_score("getData", "Record", ["id", "email", "createdAt"])
        assert with_email > base

    def test_ownership_field_boosts_score(self):
        base = _heuristic_score("getItem", "Item", [])
        with_owner = _heuristic_score("getItem", "Item", ["id", "user_id", "title"])
        assert with_owner > base

    def test_multiple_private_tokens(self):
        score = _heuristic_score("getUserProfile", "UserProfile", [])
        assert score >= 4  # "user" +2 + "user" +2 (in both name and type)

    def test_neutral_endpoint(self):
        # Completely neutral name
        score = _heuristic_score("getData", "Record", [])
        assert -1 < score < 2


# ── EndpointPrivacyClassifier — heuristic only ────────────────────────────────

class TestEndpointPrivacyClassifierHeuristic:
    def setup_method(self):
        self.clf = EndpointPrivacyClassifier()

    # Private classifications
    def test_get_user_order(self):
        assert self.clf.classify("getUserOrder", "Order", ["id", "userId", "total"]) == "private"

    def test_get_my_profile(self):
        assert self.clf.classify("getMyProfile", "Profile", ["id", "email"]) == "private"

    def test_get_account(self):
        assert self.clf.classify("getAccount", "Account", []) == "private"

    def test_list_messages(self):
        assert self.clf.classify("listMessages", "Message", []) == "private"

    def test_get_payment(self):
        assert self.clf.classify("getPayment", "Payment", ["id", "amount"]) == "private"

    # Public classifications
    def test_get_books(self):
        assert self.clf.classify("getBooks", "Book", ["id", "title", "author"]) == "public"

    def test_search_products(self):
        assert self.clf.classify("searchProducts", "Product", ["id", "name", "price"]) == "public"

    def test_get_movie(self):
        assert self.clf.classify("getMovie", "Movie", ["id", "title", "year"]) == "public"

    def test_browse_events(self):
        assert self.clf.classify("browseEvents", "Event", ["id", "name", "date"]) == "public"

    def test_list_categories(self):
        assert self.clf.classify("listCategories", "Category", ["id", "name"]) == "public"

    # Ambiguous (no LLM)
    def test_ambiguous_returns_unknown_without_llm(self):
        # "getData" with no sensitive fields and a neutral return type
        with patch("graphqler.config.USE_LLM", False):
            result = self.clf.classify("getData", "Record", [])
            assert result == "unknown"

    def test_sensitive_field_can_push_neutral_to_private(self):
        # Neutral name + sensitive field(s) should tip toward private
        result = self.clf.classify("getData", "Record", ["email", "user_id"])
        # 0 (neutral tokens) + 1 (email) + 1 (user_id) = 2 → "private"
        assert result == "private"


# ── EndpointPrivacyClassifier — LLM fallback ─────────────────────────────────

class TestEndpointPrivacyClassifierLLM:
    def setup_method(self):
        self.clf = EndpointPrivacyClassifier()

    def test_llm_called_for_ambiguous_when_use_llm_true(self):
        with patch("graphqler.config.USE_LLM", True), \
             patch(
                 "graphqler.fuzzer.engine.detectors.field_fuzzing.endpoint_classifier._llm_classify",
                 return_value="private",
             ) as mock_llm:
            result = self.clf.classify("getData", "Record", [])
            mock_llm.assert_called_once()
            assert result == "private"

    def test_llm_not_called_for_clear_private(self):
        with patch("graphqler.config.USE_LLM", True), \
             patch(
                 "graphqler.fuzzer.engine.detectors.field_fuzzing.endpoint_classifier._llm_classify",
             ) as mock_llm:
            self.clf.classify("getUserOrders", "Order", [])
            mock_llm.assert_not_called()

    def test_llm_not_called_for_clear_public(self):
        with patch("graphqler.config.USE_LLM", True), \
             patch(
                 "graphqler.fuzzer.engine.detectors.field_fuzzing.endpoint_classifier._llm_classify",
             ) as mock_llm:
            self.clf.classify("getBooks", "Book", ["id", "title"])
            mock_llm.assert_not_called()

    def test_llm_returns_public(self):
        with patch("graphqler.config.USE_LLM", True), \
             patch(
                 "graphqler.fuzzer.engine.detectors.field_fuzzing.endpoint_classifier._llm_classify",
                 return_value="public",
             ):
            result = self.clf.classify("getData", "Record", [])
            assert result == "public"

    def test_llm_error_falls_back_to_unknown(self):
        with patch("graphqler.config.USE_LLM", True), \
             patch(
                 "graphqler.fuzzer.engine.detectors.field_fuzzing.endpoint_classifier._llm_classify",
                 return_value="unknown",
             ):
            result = self.clf.classify("getData", "Record", [])
            assert result == "unknown"


# ── IDEnumerationDetector scope guard ─────────────────────────────────────────

class TestIDEnumerationDetectorScopeGuard:
    """Smoke tests for the scope-guard integration in detect()."""

    def _make_detector(self, query_name: str, output_type_name: str, output_fields: list[str]):
        """Build a minimal IDEnumerationDetector with mocked API and deps."""
        from graphqler.fuzzer.engine.detectors.field_fuzzing.id_enumeration_detector import IDEnumerationDetector
        from graphqler.graph.node import Node

        api = MagicMock()
        api.url = "http://fake/graphql"
        api.queries = {
            query_name: {
                "inputs": {"id": {"kind": "SCALAR", "name": "id", "type": "Int", "ofType": None}},
                "output": {
                    "kind": "NON_NULL",
                    "name": None,
                    "ofType": {
                        "kind": "OBJECT",
                        "name": output_type_name,
                        "ofType": None,
                        "type": output_type_name,
                    },
                    "type": None,
                },
            }
        }
        api.objects = {
            output_type_name: {
                "fields": [{"name": f} for f in output_fields],
            }
        }

        node = Node(graphql_type="Query", name=query_name, body={})
        bucket = MagicMock()
        detector = IDEnumerationDetector(
            api=api,
            node=node,
            objects_bucket=bucket,
            graphql_type="Query",
        )
        return detector

    def test_public_endpoint_skipped(self):
        """A book catalogue endpoint should be skipped — no IDOR probe."""
        detector = self._make_detector("getBooks", "Book", ["id", "title", "author"])
        with patch("graphqler.config.SKIP_ENUMERATION_ATTACKS", False), \
             patch("graphqler.config.ID_ENUMERATION_SCOPE_HEURISTIC", True), \
             patch.object(detector, "_probe_ids") as mock_probe:
            result = detector.detect()
            assert result == (False, False)
            mock_probe.assert_not_called()

    def test_private_endpoint_probed(self):
        """A user-orders endpoint should reach _probe_ids."""
        detector = self._make_detector("getUserOrder", "Order", ["id", "userId", "total"])
        with patch("graphqler.config.SKIP_ENUMERATION_ATTACKS", False), \
             patch("graphqler.config.ID_ENUMERATION_SCOPE_HEURISTIC", True), \
             patch.object(detector, "_probe_ids", return_value=(0, [])):
            detector.detect()  # result doesn't matter; we only check probe was called
            detector._probe_ids.assert_called_once()  # type: ignore[attr-defined]

    def test_scope_heuristic_disabled_runs_on_public(self):
        """When scope heuristic is off, even public endpoints get probed."""
        detector = self._make_detector("getBooks", "Book", ["id", "title"])
        with patch("graphqler.config.SKIP_ENUMERATION_ATTACKS", False), \
             patch("graphqler.config.ID_ENUMERATION_SCOPE_HEURISTIC", False), \
             patch.object(detector, "_probe_ids", return_value=(0, [])):
            detector.detect()
            detector._probe_ids.assert_called_once()  # type: ignore[attr-defined]

    def test_get_return_type_info_extracts_correctly(self):
        detector = self._make_detector("getOrder", "Order", ["id", "userId", "total"])
        type_name, fields = detector._get_return_type_info()
        assert type_name == "Order"
        assert "userId" in fields
        assert "id" in fields
