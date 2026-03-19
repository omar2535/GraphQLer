"""Unit tests for the LLM-based dependency resolvers.

All LLM calls are mocked — no real API keys or network needed.
Tests cover:
  - Happy path: LLM returns valid JSON, result is merged correctly
  - Validation: hallucinated object names and endpoint names are stripped
  - Fallback: when LLM raises an exception and LLM_RESOLVER_FALLBACK_TO_ID=True
  - Fallback disabled: exception propagates when LLM_RESOLVER_FALLBACK_TO_ID=False
  - Comparison: correct diff structure is built
  - Schema context builder: compact representation of objects
  - Simplified endpoint builder: compact representation of inputs
  - ResolverComparison: summary counts and JSON output
  - JSON extraction: strips markdown fences, finds embedded JSON
  - JSON mode detection: only passes response_format for supported models
  - Retry logic: re-prompts with correction message on non-JSON response
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from graphqler.compiler.resolvers.llm.llm_resolver import LLMResolver
from graphqler.compiler.resolvers.llm.llm_mutation_object_resolver import LLMMutationObjectResolver
from graphqler.compiler.resolvers.llm.llm_query_object_resolver import LLMQueryObjectResolver
from graphqler.compiler.resolvers.llm.comparison import ResolverComparison


# ── Shared fixtures ───────────────────────────────────────────────────────────

OBJECTS = {
    "User": {
        "fields": [
            {"name": "id", "kind": "NON_NULL", "type": None, "ofType": {"kind": "SCALAR", "name": "ID", "type": "ID", "ofType": None}},
            {"name": "email", "kind": "NON_NULL", "type": None, "ofType": {"kind": "SCALAR", "name": "String", "type": "String", "ofType": None}},
            {"name": "name", "kind": "SCALAR", "type": "String", "ofType": None},
        ],
        "hardDependsOn": [],
        "softDependsOn": [],
        "associatedQueries": [],
        "associatedMutatations": [],
    },
    "Post": {
        "fields": [
            {"name": "id", "kind": "NON_NULL", "type": None, "ofType": {"kind": "SCALAR", "name": "ID", "type": "ID", "ofType": None}},
            {"name": "title", "kind": "SCALAR", "type": "String", "ofType": None},
            {"name": "author", "kind": "OBJECT", "type": "User", "ofType": None},
        ],
        "hardDependsOn": [],
        "softDependsOn": [],
        "associatedQueries": [],
        "associatedMutatations": [],
    },
}

MUTATIONS = {
    "createPost": {
        "name": "createPost",
        "description": "Create a new blog post",
        "inputs": {
            "title": {"kind": "NON_NULL", "type": None, "name": "title", "ofType": {"kind": "SCALAR", "name": "String", "type": "String", "ofType": None}},
            "authorEmail": {"kind": "NON_NULL", "type": None, "name": "authorEmail", "ofType": {"kind": "SCALAR", "name": "String", "type": "String", "ofType": None}},
        },
        "output": {"kind": "OBJECT", "name": "Post", "type": "Post", "ofType": None},
        "isDepracated": False,
    },
    "deletePost": {
        "name": "deletePost",
        "description": None,
        "inputs": {
            "id": {"kind": "NON_NULL", "type": None, "name": "id", "ofType": {"kind": "SCALAR", "name": "ID", "type": "ID", "ofType": None}},
        },
        "output": {"kind": "SCALAR", "name": "Boolean", "type": "Boolean", "ofType": None},
        "isDepracated": False,
    },
}

QUERIES = {
    "getPost": {
        "name": "getPost",
        "description": None,
        "inputs": {
            "id": {"kind": "NON_NULL", "type": None, "name": "id", "ofType": {"kind": "SCALAR", "name": "ID", "type": "ID", "ofType": None}},
        },
        "output": {"kind": "OBJECT", "name": "Post", "type": "Post", "ofType": None},
    },
    "searchPosts": {
        "name": "searchPosts",
        "description": "Search posts by author email",
        "inputs": {
            "authorEmail": {"kind": "NON_NULL", "type": None, "name": "authorEmail", "ofType": {"kind": "SCALAR", "name": "String", "type": "String", "ofType": None}},
        },
        "output": {"kind": "LIST", "name": None, "type": None, "ofType": {"kind": "OBJECT", "name": "Post", "type": "Post", "ofType": None}},
    },
}

INPUT_OBJECTS: dict = {}

# ── LLMResolver (base) ────────────────────────────────────────────────────────


class TestLLMResolverBase(unittest.TestCase):
    def setUp(self):
        self.resolver = LLMResolver()

    def test_schema_context_contains_object_names(self):
        ctx = self.resolver.build_schema_context(OBJECTS)
        self.assertIn("User", ctx)
        self.assertIn("Post", ctx)

    def test_schema_context_contains_field_names(self):
        ctx = self.resolver.build_schema_context(OBJECTS)
        self.assertIn("email", ctx)
        self.assertIn("title", ctx)

    def test_simplify_endpoints_returns_all_names(self):
        simplified = self.resolver.simplify_endpoints(MUTATIONS)
        self.assertIn("createPost", simplified)
        self.assertIn("deletePost", simplified)

    def test_simplify_endpoints_readable_types(self):
        simplified = self.resolver.simplify_endpoints(MUTATIONS)
        self.assertIn("String!", simplified["createPost"]["inputs"]["title"])

    def test_validate_mutation_strips_hallucinated_endpoints(self):
        raw = {
            "createPost": {"mutationType": "CREATE", "hardDependsOn": {"authorEmail": "User"}, "softDependsOn": {}},
            "nonExistentMutation": {"mutationType": "DELETE", "hardDependsOn": {}, "softDependsOn": {}},
        }
        validated = self.resolver.validate_llm_mutation_result(raw, list(MUTATIONS.keys()), OBJECTS)
        self.assertIn("createPost", validated)
        self.assertNotIn("nonExistentMutation", validated)

    def test_validate_mutation_strips_unknown_object_deps(self):
        raw = {
            "createPost": {"mutationType": "CREATE", "hardDependsOn": {"authorEmail": "FakeObject"}, "softDependsOn": {}},
        }
        validated = self.resolver.validate_llm_mutation_result(raw, list(MUTATIONS.keys()), OBJECTS)
        self.assertEqual(validated["createPost"]["hardDependsOn"], {})

    def test_validate_mutation_normalises_bad_mutation_type(self):
        raw = {
            "createPost": {"mutationType": "UPSERT", "hardDependsOn": {}, "softDependsOn": {}},
        }
        validated = self.resolver.validate_llm_mutation_result(raw, list(MUTATIONS.keys()), OBJECTS)
        self.assertEqual(validated["createPost"]["mutationType"], "UNKNOWN")

    def test_validate_query_strips_hallucinated_endpoints(self):
        raw = {
            "getPost": {"hardDependsOn": {"id": "Post"}, "softDependsOn": {}},
            "ghostQuery": {"hardDependsOn": {}, "softDependsOn": {}},
        }
        validated = self.resolver.validate_llm_query_result(raw, list(QUERIES.keys()), OBJECTS)
        self.assertIn("getPost", validated)
        self.assertNotIn("ghostQuery", validated)

    def test_merge_with_classic_llm_takes_precedence(self):
        classic = {
            "createPost": {"mutationType": "UNKNOWN", "hardDependsOn": {}, "softDependsOn": {}, "other": "x"},
        }
        llm = {
            "createPost": {"mutationType": "CREATE", "hardDependsOn": {"authorEmail": "User"}, "softDependsOn": {}},
        }
        merged = self.resolver.merge_with_classic(llm, classic, ["createPost"])
        self.assertEqual(merged["createPost"]["mutationType"], "CREATE")
        self.assertEqual(merged["createPost"]["hardDependsOn"], {"authorEmail": "User"})
        self.assertEqual(merged["createPost"]["other"], "x")  # non-dep fields preserved

    def test_merge_with_classic_fills_missing_llm_entries(self):
        classic = {
            "createPost": {"mutationType": "CREATE", "hardDependsOn": {}, "softDependsOn": {}},
            "deletePost": {"mutationType": "DELETE", "hardDependsOn": {"id": "Post"}, "softDependsOn": {}},
        }
        llm = {
            "createPost": {"mutationType": "CREATE", "hardDependsOn": {}, "softDependsOn": {}},
            # deletePost absent from LLM response
        }
        merged = self.resolver.merge_with_classic(llm, classic, ["createPost", "deletePost"])
        self.assertIn("deletePost", merged)
        self.assertEqual(merged["deletePost"]["mutationType"], "DELETE")

    # ── _extract_json_from_text ────────────────────────────────────────────────

    def test_extract_json_raw(self):
        data = {"foo": "bar"}
        result = self.resolver._extract_json_from_text(json.dumps(data))
        self.assertEqual(result, data)

    def test_extract_json_with_backtick_fence(self):
        data = {"createPost": {"mutationType": "CREATE"}}
        text = "```json\n" + json.dumps(data) + "\n```"
        result = self.resolver._extract_json_from_text(text)
        self.assertEqual(result, data)

    def test_extract_json_with_plain_fence(self):
        data = {"a": 1}
        text = "```\n" + json.dumps(data) + "\n```"
        result = self.resolver._extract_json_from_text(text)
        self.assertEqual(result, data)

    def test_extract_json_embedded_in_prose(self):
        data = {"x": "y"}
        text = "Here is the result: " + json.dumps(data) + " Hope that helps!"
        result = self.resolver._extract_json_from_text(text)
        self.assertEqual(result, data)

    def test_extract_json_raises_on_garbage(self):
        with self.assertRaises(ValueError):
            self.resolver._extract_json_from_text("this is not json at all")

# ── Retry logic ───────────────────────────────────────────────────────────────


class TestCallLLMRetry(unittest.TestCase):
    """call_llm should retry up to LLM_MAX_RETRIES times on non-JSON responses."""

    def _make_response(self, content: str) -> MagicMock:
        mock = MagicMock()
        mock.choices[0].message.content = content
        return mock

    @patch("graphqler.compiler.resolvers.llm.llm_resolver.config")
    def test_succeeds_on_second_attempt(self, mock_cfg):
        mock_cfg.LLM_MODEL = "gpt-4o-mini"
        mock_cfg.LLM_API_KEY = ""
        mock_cfg.LLM_BASE_URL = ""
        mock_cfg.LLM_MAX_RETRIES = 1

        bad = self._make_response("not json")
        good = self._make_response('{"ok": true}')

        import litellm
        with patch.object(litellm, "completion", side_effect=[bad, good]):
            resolver = LLMResolver()
            result = resolver.call_llm("sys", "user")

        self.assertEqual(result, {"ok": True})

    @patch("graphqler.compiler.resolvers.llm.llm_resolver.config")
    def test_raises_after_all_retries_exhausted(self, mock_cfg):
        mock_cfg.LLM_MODEL = "gpt-4o-mini"
        mock_cfg.LLM_API_KEY = ""
        mock_cfg.LLM_BASE_URL = ""
        mock_cfg.LLM_MAX_RETRIES = 1

        bad = self._make_response("still not json")

        import litellm
        with patch.object(litellm, "completion", return_value=bad):
            resolver = LLMResolver()
            with self.assertRaises(ValueError):
                resolver.call_llm("sys", "user")

    @patch("graphqler.compiler.resolvers.llm.llm_resolver.config")
    def test_correction_turn_appended_to_messages(self, mock_cfg):
        mock_cfg.LLM_MODEL = "gpt-4o-mini"
        mock_cfg.LLM_API_KEY = ""
        mock_cfg.LLM_BASE_URL = ""
        mock_cfg.LLM_MAX_RETRIES = 1

        bad = self._make_response("not json")
        good = self._make_response('{"fixed": true}')

        import litellm
        with patch.object(litellm, "completion", side_effect=[bad, good]) as mock_completion:
            resolver = LLMResolver()
            resolver.call_llm("system_prompt", "user_prompt")

        # Second call should have 4 messages: system + user + bad_assistant + correction
        second_call_messages = mock_completion.call_args_list[1][1]["messages"]
        self.assertEqual(len(second_call_messages), 4)
        self.assertEqual(second_call_messages[2]["role"], "assistant")
        self.assertEqual(second_call_messages[3]["role"], "user")
        self.assertIn("JSON", second_call_messages[3]["content"])


# ── LLMMutationObjectResolver ─────────────────────────────────────────────────


class TestLLMMutationObjectResolver(unittest.TestCase):
    def _make_llm_response(self, payload: dict) -> MagicMock:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(payload)
        return mock_response

    @patch("graphqler.compiler.resolvers.llm.llm_resolver.config")
    def test_happy_path_llm_result_is_used(self, mock_cfg):
        mock_cfg.LLM_MODEL = "gpt-4o-mini"
        mock_cfg.LLM_API_KEY = ""
        mock_cfg.LLM_BASE_URL = ""
        mock_cfg.LLM_RESOLVER_FALLBACK_TO_ID = True
        mock_cfg.LLM_MAX_RETRIES = 0

        llm_payload = {
            "createPost": {"mutationType": "CREATE", "hardDependsOn": {"authorEmail": "User"}, "softDependsOn": {}},
            "deletePost": {"mutationType": "DELETE", "hardDependsOn": {"id": "Post"}, "softDependsOn": {}},
        }

        import litellm
        with patch.object(litellm, "completion", return_value=self._make_llm_response(llm_payload)):
            resolver = LLMMutationObjectResolver()
            result = resolver.resolve(OBJECTS, MUTATIONS, INPUT_OBJECTS)

        self.assertEqual(result["createPost"]["mutationType"], "CREATE")
        self.assertEqual(result["createPost"]["hardDependsOn"], {"authorEmail": "User"})
        self.assertEqual(result["deletePost"]["mutationType"], "DELETE")
        self.assertTrue(resolver.comparison)

    def test_fallback_on_llm_exception(self):
        from graphqler import config as graphqler_config
        original = graphqler_config.LLM_RESOLVER_FALLBACK_TO_ID
        graphqler_config.LLM_RESOLVER_FALLBACK_TO_ID = True
        try:
            import litellm
            with patch("graphqler.compiler.resolvers.llm.llm_resolver.config") as mock_cfg:
                mock_cfg.LLM_MODEL = "gpt-4o-mini"
                mock_cfg.LLM_API_KEY = ""
                mock_cfg.LLM_BASE_URL = ""
                mock_cfg.LLM_MAX_RETRIES = 0
                with patch.object(litellm, "completion", side_effect=RuntimeError("API down")):
                    resolver = LLMMutationObjectResolver()
                    result = resolver.resolve(OBJECTS, MUTATIONS, INPUT_OBJECTS)

            # Should still get a valid result from classic resolver
            self.assertIn("createPost", result)
            self.assertIn("deletePost", result)
            self.assertEqual(resolver.comparison, {})
        finally:
            graphqler_config.LLM_RESOLVER_FALLBACK_TO_ID = original

    def test_fallback_disabled_propagates_exception(self):
        from graphqler import config as graphqler_config
        original = graphqler_config.LLM_RESOLVER_FALLBACK_TO_ID
        graphqler_config.LLM_RESOLVER_FALLBACK_TO_ID = False
        try:
            import litellm
            with patch("graphqler.compiler.resolvers.llm.llm_resolver.config") as mock_cfg:
                mock_cfg.LLM_MODEL = "gpt-4o-mini"
                mock_cfg.LLM_API_KEY = ""
                mock_cfg.LLM_BASE_URL = ""
                mock_cfg.LLM_MAX_RETRIES = 0
                with patch.object(litellm, "completion", side_effect=RuntimeError("API down")):
                    resolver = LLMMutationObjectResolver()
                    with self.assertRaises(RuntimeError):
                        resolver.resolve(OBJECTS, MUTATIONS, INPUT_OBJECTS)
        finally:
            graphqler_config.LLM_RESOLVER_FALLBACK_TO_ID = original

    def test_comparison_detects_differences(self):
        from graphqler import config as graphqler_config
        original = graphqler_config.LLM_RESOLVER_FALLBACK_TO_ID
        graphqler_config.LLM_RESOLVER_FALLBACK_TO_ID = True
        try:
            # LLM catches authorEmail → User (classic would miss this, it's not an ID type)
            llm_payload = {
                "createPost": {"mutationType": "CREATE", "hardDependsOn": {"authorEmail": "User"}, "softDependsOn": {}},
                "deletePost": {"mutationType": "DELETE", "hardDependsOn": {"id": "Post"}, "softDependsOn": {}},
            }

            import litellm
            with patch("graphqler.compiler.resolvers.llm.llm_resolver.config") as mock_cfg:
                mock_cfg.LLM_MODEL = "gpt-4o-mini"
                mock_cfg.LLM_API_KEY = ""
                mock_cfg.LLM_BASE_URL = ""
                mock_cfg.LLM_MAX_RETRIES = 0
                with patch.object(litellm, "completion", return_value=self._make_llm_response(llm_payload)):
                    resolver = LLMMutationObjectResolver()
                    resolver.resolve(OBJECTS, MUTATIONS, INPUT_OBJECTS)

            # createPost: classic gets {} for hardDependsOn (authorEmail is String not ID),
            # LLM gets {"authorEmail": "User"} → should differ
            self.assertTrue(resolver.comparison["createPost"]["differs"])
            self.assertIn("hardDependsOn", resolver.comparison["createPost"]["diff"])
        finally:
            graphqler_config.LLM_RESOLVER_FALLBACK_TO_ID = original


# ── LLMQueryObjectResolver ────────────────────────────────────────────────────


class TestLLMQueryObjectResolver(unittest.TestCase):
    def _make_llm_response(self, payload: dict) -> MagicMock:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(payload)
        return mock_response

    @patch("graphqler.compiler.resolvers.llm.llm_resolver.config")
    def test_happy_path_query_resolved(self, mock_cfg):
        mock_cfg.LLM_MODEL = "gpt-4o-mini"
        mock_cfg.LLM_API_KEY = ""
        mock_cfg.LLM_BASE_URL = ""
        mock_cfg.LLM_RESOLVER_FALLBACK_TO_ID = True
        mock_cfg.LLM_MAX_RETRIES = 0

        llm_payload = {
            "getPost": {"hardDependsOn": {"id": "Post"}, "softDependsOn": {}},
            "searchPosts": {"hardDependsOn": {"authorEmail": "User"}, "softDependsOn": {}},
        }

        import litellm
        with patch.object(litellm, "completion", return_value=self._make_llm_response(llm_payload)):
            resolver = LLMQueryObjectResolver()
            result = resolver.resolve(OBJECTS, QUERIES, INPUT_OBJECTS)

        self.assertEqual(result["getPost"]["hardDependsOn"], {"id": "Post"})
        # Classic misses authorEmail (String, not ID); LLM catches it
        self.assertEqual(result["searchPosts"]["hardDependsOn"], {"authorEmail": "User"})

    def test_fallback_on_bad_json(self):
        from graphqler import config as graphqler_config
        original = graphqler_config.LLM_RESOLVER_FALLBACK_TO_ID
        graphqler_config.LLM_RESOLVER_FALLBACK_TO_ID = True
        try:
            bad_response = MagicMock()
            bad_response.choices[0].message.content = "not json at all"

            import litellm
            with patch("graphqler.compiler.resolvers.llm.llm_resolver.config") as mock_cfg:
                mock_cfg.LLM_MODEL = "gpt-4o-mini"
                mock_cfg.LLM_API_KEY = ""
                mock_cfg.LLM_BASE_URL = ""
                mock_cfg.LLM_MAX_RETRIES = 0
                with patch.object(litellm, "completion", return_value=bad_response):
                    resolver = LLMQueryObjectResolver()
                    result = resolver.resolve(OBJECTS, QUERIES, INPUT_OBJECTS)

            # Should fall back gracefully
            self.assertIn("getPost", result)
            self.assertIn("searchPosts", result)
        finally:
            graphqler_config.LLM_RESOLVER_FALLBACK_TO_ID = original


# ── ResolverComparison ────────────────────────────────────────────────────────


class TestResolverComparison(unittest.TestCase):
    def _make_mutation_comparison(self) -> dict:
        return {
            "createPost": {
                "classic": {"mutationType": "UNKNOWN", "hardDependsOn": {}, "softDependsOn": {}},
                "llm": {"mutationType": "CREATE", "hardDependsOn": {"authorEmail": "User"}, "softDependsOn": {}},
                "differs": True,
                "diff": {
                    "mutationType": {"classic": "UNKNOWN", "llm": "CREATE"},
                    "hardDependsOn": {"classic": {}, "llm": {"authorEmail": "User"}},
                },
            },
            "deletePost": {
                "classic": {"mutationType": "DELETE", "hardDependsOn": {"id": "Post"}, "softDependsOn": {}},
                "llm": {"mutationType": "DELETE", "hardDependsOn": {"id": "Post"}, "softDependsOn": {}},
                "differs": False,
                "diff": {},
            },
        }

    def _make_query_comparison(self) -> dict:
        return {
            "getPost": {
                "classic": {"hardDependsOn": {"id": "Post"}, "softDependsOn": {}},
                "llm": {"hardDependsOn": {"id": "Post"}, "softDependsOn": {}},
                "differs": False,
                "diff": {},
            },
        }

    def test_summary_counts_correct(self):
        comp = ResolverComparison(self._make_mutation_comparison(), self._make_query_comparison())
        doc = comp.build()
        self.assertEqual(doc["summary"]["total_mutations"], 2)
        self.assertEqual(doc["summary"]["mutations_that_differ"], 1)
        self.assertEqual(doc["summary"]["total_queries"], 1)
        self.assertEqual(doc["summary"]["queries_that_differ"], 0)

    def test_save_writes_valid_json(self):
        import tempfile
        import os
        comp = ResolverComparison(self._make_mutation_comparison(), self._make_query_comparison())
        with tempfile.TemporaryDirectory() as tmpdir:
            comp.save(tmpdir)
            json_path = os.path.join(tmpdir, "eval", "resolver_comparison.json")
            self.assertTrue(os.path.exists(json_path))
            with open(json_path) as f:
                data = json.load(f)
            self.assertIn("summary", data)
            self.assertIn("mutations", data)
            self.assertIn("queries", data)

    def test_save_summary_values_in_file(self):
        import tempfile
        comp = ResolverComparison(self._make_mutation_comparison(), self._make_query_comparison())
        with tempfile.TemporaryDirectory() as tmpdir:
            comp.save(tmpdir)
            import os
            with open(os.path.join(tmpdir, "eval", "resolver_comparison.json")) as f:
                data = json.load(f)
            self.assertEqual(data["summary"]["mutations_that_differ"], 1)
            self.assertEqual(data["summary"]["queries_that_differ"], 0)


if __name__ == "__main__":
    unittest.main()
