"""Unit tests for the cursor utilities, heuristic classifier, and PaginationCursorStrategy."""

import unittest
import base64
import json

from graphqler.graph.node import Node
from graphqler.chains.cursor import cursor_utils, heuristic_cursor_classifier
from graphqler.chains.strategies.pagination_cursor_strategy import PaginationCursorStrategy


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_node(graphql_type: str, name: str, body: dict | None = None) -> Node:
    return Node(graphql_type=graphql_type, name=name, body=body or {})


def _b64(data: dict | str) -> str:
    """Encode a dict or string as a base64 cursor string (same as encode_cursor)."""
    raw = json.dumps(data, separators=(",", ":")) if isinstance(data, dict) else str(data)
    return base64.b64encode(raw.encode()).decode("ascii")


# ══════════════════════════════════════════════════════════════════════════════
# cursor_utils
# ══════════════════════════════════════════════════════════════════════════════

class TestDecodeCursor(unittest.TestCase):

    def test_decode_json_dict(self):
        encoded = _b64({"id": 42, "type": "Post"})
        result = cursor_utils.decode_cursor(encoded)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], 42)

    def test_decode_plain_string(self):
        encoded = _b64("cursor:42")
        result = cursor_utils.decode_cursor(encoded)
        self.assertEqual(result, "cursor:42")

    def test_decode_invalid_returns_original(self):
        result = cursor_utils.decode_cursor("not_valid_base64!!!")
        self.assertEqual(result, "not_valid_base64!!!")

    def test_decode_then_encode_roundtrip(self):
        original = {"id": 7, "type": "User"}
        encoded = cursor_utils.encode_cursor(original)
        decoded = cursor_utils.decode_cursor(encoded)
        self.assertEqual(decoded, original)


class TestEncodeCursor(unittest.TestCase):

    def test_encode_dict(self):
        data = {"id": 1}
        result = cursor_utils.encode_cursor(data)
        # Should be valid base64
        decoded_raw = base64.b64decode(result).decode()
        self.assertEqual(json.loads(decoded_raw), data)

    def test_encode_string(self):
        result = cursor_utils.encode_cursor("hello")
        decoded_raw = base64.b64decode(result).decode()
        self.assertEqual(decoded_raw, "hello")


class TestExtractCursorFromResponse(unittest.TestCase):

    def test_finds_end_cursor(self):
        data = {"posts": {"pageInfo": {"endCursor": "abc123", "hasNextPage": True}}}
        cursors = cursor_utils.extract_cursor_from_response(data)
        self.assertIn("abc123", cursors)

    def test_finds_cursor_in_edges(self):
        data = {"posts": {"edges": [{"cursor": "edge1"}, {"cursor": "edge2"}]}}
        cursors = cursor_utils.extract_cursor_from_response(data)
        self.assertIn("edge1", cursors)
        self.assertIn("edge2", cursors)

    def test_empty_on_no_cursor(self):
        data = {"user": {"id": "1", "name": "Alice"}}
        cursors = cursor_utils.extract_cursor_from_response(data)
        self.assertEqual(cursors, [])

    def test_ignores_null_cursor(self):
        data = {"posts": {"pageInfo": {"endCursor": None}}}
        cursors = cursor_utils.extract_cursor_from_response(data)
        self.assertEqual(cursors, [])


class TestMutateForIdor(unittest.TestCase):

    def test_produces_variants_for_int_field(self):
        cursor = cursor_utils.encode_cursor({"id": 5})
        variants = cursor_utils.mutate_for_idor(cursor)
        self.assertTrue(len(variants) > 0)
        # Each variant should decode to a dict with a different id
        ids = set()
        for v in variants:
            decoded = cursor_utils.decode_cursor(v)
            if isinstance(decoded, dict):
                ids.add(decoded.get("id"))
        self.assertGreater(len(ids), 1)

    def test_original_not_in_variants(self):
        cursor = cursor_utils.encode_cursor({"id": 5})
        variants = cursor_utils.mutate_for_idor(cursor)
        self.assertNotIn(cursor, variants)

    def test_no_int_fields_returns_original(self):
        cursor = cursor_utils.encode_cursor({"type": "Post"})
        variants = cursor_utils.mutate_for_idor(cursor)
        self.assertEqual(variants, [cursor])

    def test_non_base64_returns_original(self):
        variants = cursor_utils.mutate_for_idor("plain-cursor")
        self.assertEqual(variants, ["plain-cursor"])


class TestMutateForInjection(unittest.TestCase):

    def test_produces_sql_payload_variants(self):
        cursor = cursor_utils.encode_cursor({"query": "getPost"})
        variants = cursor_utils.mutate_for_injection(cursor)
        self.assertTrue(len(variants) > 0)
        # At least one variant should contain an injection payload
        decoded_values = []
        for v in variants:
            d = cursor_utils.decode_cursor(v)
            if isinstance(d, dict):
                decoded_values.extend(d.values())
        has_injection = any("OR" in str(v) or "sleep" in str(v).lower() or ".." in str(v) for v in decoded_values)
        self.assertTrue(has_injection)

    def test_no_string_fields_encodes_raw_payloads(self):
        cursor = cursor_utils.encode_cursor({"id": 1})
        variants = cursor_utils.mutate_for_injection(cursor)
        # Should still produce non-empty variants by encoding raw payloads
        self.assertTrue(len(variants) > 0)

    def test_all_variants_are_unique(self):
        cursor = cursor_utils.encode_cursor({"query": "abc"})
        variants = cursor_utils.mutate_for_injection(cursor)
        self.assertEqual(len(variants), len(set(variants)))


# ══════════════════════════════════════════════════════════════════════════════
# heuristic_cursor_classifier
# ══════════════════════════════════════════════════════════════════════════════

class TestHeuristicCursorClassifier(unittest.TestCase):

    def test_non_query_scores_zero(self):
        node = _make_node("Mutation", "createPost")
        score, reason = heuristic_cursor_classifier.classify(node)
        self.assertEqual(score, 0.0)
        self.assertIn("not a Query node", reason)

    def test_relay_annotation_scores_high(self):
        node = _make_node("Query", "posts", body={
            "inputs": {},
            "pagination": {"style": "relay", "cursor_arg": "after", "size_arg": "first"},
        })
        score, reason = heuristic_cursor_classifier.classify(node)
        self.assertGreaterEqual(score, 0.9)
        self.assertIn("relay-annotation", reason)

    def test_after_and_first_args_score_high(self):
        node = _make_node("Query", "listPosts", body={
            "inputs": {
                "after": {"kind": "SCALAR", "name": "after", "type": "String"},
                "first": {"kind": "SCALAR", "name": "first", "type": "Int"},
            },
        })
        score, reason = heuristic_cursor_classifier.classify(node)
        self.assertGreaterEqual(score, 0.85)

    def test_after_arg_alone_scores_moderately(self):
        node = _make_node("Query", "listPosts", body={
            "inputs": {"after": {"kind": "SCALAR", "name": "after", "type": "String"}},
        })
        score, _ = heuristic_cursor_classifier.classify(node)
        self.assertGreaterEqual(score, 0.7)

    def test_connection_return_type_scores(self):
        node = _make_node("Query", "usersPaginated", body={
            "inputs": {},
            "output": {"kind": "OBJECT", "name": "UserConnection"},
        })
        score, reason = heuristic_cursor_classifier.classify(node)
        self.assertGreaterEqual(score, 0.5)
        self.assertIn("connection-type", reason)

    def test_offset_arg_scores_low(self):
        node = _make_node("Query", "listItems", body={
            "inputs": {"offset": {"kind": "SCALAR", "name": "offset", "type": "Int"}},
        })
        score, _ = heuristic_cursor_classifier.classify(node)
        self.assertGreaterEqual(score, 0.2)
        self.assertLess(score, 0.5)

    def test_no_signals_scores_zero(self):
        node = _make_node("Query", "getUser", body={
            "inputs": {"userId": {"kind": "SCALAR", "name": "userId", "type": "ID"}},
        })
        score, reason = heuristic_cursor_classifier.classify(node)
        self.assertEqual(score, 0.0)
        self.assertIn("no pagination signals", reason)

    def test_connection_type_in_non_null_wrapper(self):
        """Return type wrapped in NON_NULL should still be detected."""
        node = _make_node("Query", "searchResults", body={
            "inputs": {},
            "output": {
                "kind": "NON_NULL",
                "name": None,
                "ofType": {"kind": "OBJECT", "name": "SearchConnection", "ofType": None},
            },
        })
        score, reason = heuristic_cursor_classifier.classify(node)
        self.assertGreaterEqual(score, 0.5)
        self.assertIn("connection-type", reason)


# ══════════════════════════════════════════════════════════════════════════════
# PaginationCursorStrategy
# ══════════════════════════════════════════════════════════════════════════════

class TestPaginationCursorStrategy(unittest.TestCase):

    def setUp(self):
        self.strategy = PaginationCursorStrategy()

    def test_is_enabled_by_default(self):
        import graphqler.config as cfg
        original = cfg.SKIP_CURSOR_CHAIN_FUZZING
        try:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = False
            self.assertTrue(self.strategy.is_enabled())
        finally:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = original

    def test_is_disabled_when_skipped(self):
        import graphqler.config as cfg
        original = cfg.SKIP_CURSOR_CHAIN_FUZZING
        try:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = True
            self.assertFalse(self.strategy.is_enabled())
        finally:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = original

    def test_returns_empty_when_disabled(self):
        import graphqler.config as cfg
        original = cfg.SKIP_CURSOR_CHAIN_FUZZING
        try:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = True
            result = self.strategy.generate(None, [])
            self.assertEqual(result, [])
        finally:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = original

    def test_returns_empty_when_graph_is_none(self):
        import graphqler.config as cfg
        original = cfg.SKIP_CURSOR_CHAIN_FUZZING
        try:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = False
            result = self.strategy.generate(None, [])
            self.assertEqual(result, [])
        finally:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = original

    def test_generates_injection_chain_for_relay_node(self):
        import graphqler.config as cfg
        import networkx as nx
        original_skip = cfg.SKIP_CURSOR_CHAIN_FUZZING
        original_threshold = cfg.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD
        original_cursor_auth = cfg.CURSOR_SECONDARY_AUTH
        try:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = False
            cfg.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD = 0.5
            cfg.CURSOR_SECONDARY_AUTH = None

            node = _make_node("Query", "listPosts", body={
                "inputs": {
                    "after": {"kind": "SCALAR", "name": "after", "type": "String"},
                    "first": {"kind": "SCALAR", "name": "first", "type": "Int"},
                },
            })
            graph = nx.DiGraph()
            graph.add_node(node)

            chains = self.strategy.generate(graph, [])
            self.assertTrue(len(chains) >= 1)
            injection_chain = next(
                (c for c in chains if "cursor_injection" in c.name), None
            )
            self.assertIsNotNone(injection_chain)
            # Step 1 should be primary, step 2 cursor_injection
            self.assertEqual(injection_chain.steps[0].profile_name, "primary")
            self.assertEqual(injection_chain.steps[1].profile_name, "cursor_injection")
        finally:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = original_skip
            cfg.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD = original_threshold
            cfg.CURSOR_SECONDARY_AUTH = original_cursor_auth

    def test_generates_idor_chain_when_cursor_auth_set(self):
        import graphqler.config as cfg
        import networkx as nx
        original_skip = cfg.SKIP_CURSOR_CHAIN_FUZZING
        original_threshold = cfg.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD
        original_cursor_auth = cfg.CURSOR_SECONDARY_AUTH
        try:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = False
            cfg.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD = 0.5
            cfg.CURSOR_SECONDARY_AUTH = "Bearer secondtoken"

            node = _make_node("Query", "listPosts", body={
                "inputs": {
                    "after": {"kind": "SCALAR", "name": "after", "type": "String"},
                },
            })
            graph = nx.DiGraph()
            graph.add_node(node)

            chains = self.strategy.generate(graph, [])
            idor_chain = next((c for c in chains if "cursor_idor" in c.name), None)
            self.assertIsNotNone(idor_chain)
            self.assertEqual(idor_chain.steps[1].profile_name, "cursor_idor")
        finally:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = original_skip
            cfg.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD = original_threshold
            cfg.CURSOR_SECONDARY_AUTH = original_cursor_auth

    def test_no_idor_chain_without_cursor_auth(self):
        import graphqler.config as cfg
        import networkx as nx
        original_skip = cfg.SKIP_CURSOR_CHAIN_FUZZING
        original_threshold = cfg.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD
        original_cursor_auth = cfg.CURSOR_SECONDARY_AUTH
        try:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = False
            cfg.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD = 0.5
            cfg.CURSOR_SECONDARY_AUTH = None

            node = _make_node("Query", "listPosts", body={
                "inputs": {"after": {"kind": "SCALAR", "name": "after", "type": "String"}},
            })
            graph = nx.DiGraph()
            graph.add_node(node)

            chains = self.strategy.generate(graph, [])
            idor_chains = [c for c in chains if "cursor_idor" in c.name]
            self.assertEqual(idor_chains, [])
        finally:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = original_skip
            cfg.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD = original_threshold
            cfg.CURSOR_SECONDARY_AUTH = original_cursor_auth

    def test_mutation_nodes_are_skipped(self):
        import graphqler.config as cfg
        import networkx as nx
        original_skip = cfg.SKIP_CURSOR_CHAIN_FUZZING
        original_threshold = cfg.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD
        try:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = False
            cfg.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD = 0.5

            node = _make_node("Mutation", "createPost", body={
                "inputs": {"after": {"kind": "SCALAR", "name": "after", "type": "String"}},
            })
            graph = nx.DiGraph()
            graph.add_node(node)

            chains = self.strategy.generate(graph, [])
            self.assertEqual(chains, [])
        finally:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = original_skip
            cfg.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD = original_threshold

    def test_low_score_node_is_skipped(self):
        import graphqler.config as cfg
        import networkx as nx
        original_skip = cfg.SKIP_CURSOR_CHAIN_FUZZING
        original_threshold = cfg.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD
        try:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = False
            cfg.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD = 0.9  # Very high threshold

            node = _make_node("Query", "getUser", body={
                "inputs": {"id": {"kind": "SCALAR", "name": "id", "type": "ID"}},
            })
            graph = nx.DiGraph()
            graph.add_node(node)

            chains = self.strategy.generate(graph, [])
            self.assertEqual(chains, [])
        finally:
            cfg.SKIP_CURSOR_CHAIN_FUZZING = original_skip
            cfg.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD = original_threshold


if __name__ == "__main__":
    unittest.main()
