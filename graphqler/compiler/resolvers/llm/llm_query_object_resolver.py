"""LLM-backed query resolver.

Resolves hardDependsOn + softDependsOn for every query by asking an LLM for its
interpretation of the schema, then merging that result with the classic ID-based
resolver output.

The `.comparison` attribute (set after `resolve()`) holds the side-by-side diff
between the LLM result and the classic result for systematic analysis.
"""

import json
import copy
import logging

from graphqler import config
from graphqler.compiler.resolvers.query_object_resolver import QueryObjectResolver
from .llm_resolver import LLMResolver
from .prompt_templates import QUERY_SYSTEM_PROMPT, QUERY_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class LLMQueryObjectResolver(LLMResolver):
    """Resolves queries using an LLM, with optional fallback to the classic resolver."""

    def __init__(self):
        super().__init__()
        self.comparison: dict = {}  # populated by resolve(); keyed by query name

    def resolve(self, objects: dict, queries: dict, input_objects: dict) -> dict:
        """Resolve queries via LLM, falling back to classic resolver on failure.

        Args:
            objects (dict): Compiled objects.
            queries (dict): Raw parsed queries.
            input_objects (dict): Raw parsed input objects.

        Returns:
            dict: Queries enriched with hardDependsOn, softDependsOn.
        """
        # Always run classic resolver — used as fallback and for comparison
        classic_queries = QueryObjectResolver().resolve(objects, copy.deepcopy(queries), input_objects)

        try:
            llm_raw = self._call_llm_for_queries(objects, queries)
            llm_validated = self.validate_llm_query_result(llm_raw, list(queries.keys()), objects)
            merged = self.merge_with_classic(llm_validated, classic_queries, list(queries.keys()))
            self.comparison = self._build_comparison(classic_queries, merged, queries.keys())
            logger.info(f"LLM query resolver: resolved {len(llm_validated)}/{len(queries)} queries")
            return merged
        except Exception as exc:
            if config.LLM_RESOLVER_FALLBACK_TO_ID:
                logger.warning(f"LLM query resolver failed ({exc}), falling back to classic resolver")
                self.comparison = {}
                return classic_queries
            raise

    def _call_llm_for_queries(self, objects: dict, queries: dict) -> dict:
        """Build the prompt and call the LLM.

        Args:
            objects (dict): Compiled objects (for schema context).
            queries (dict): Raw parsed queries.

        Returns:
            dict: Raw parsed JSON response from the LLM.
        """
        schema_context = self.build_schema_context(objects)
        simplified = self.simplify_endpoints(queries)
        queries_json = json.dumps(simplified, indent=2)

        user_prompt = QUERY_USER_PROMPT_TEMPLATE.format(
            schema_context=schema_context,
            queries_json=queries_json,
        )
        return self.call_llm(QUERY_SYSTEM_PROMPT, user_prompt)

    def _build_comparison(self, classic: dict, llm_merged: dict, query_names) -> dict:
        """Build a per-query comparison dict.

        Args:
            classic (dict): Classic resolver output.
            llm_merged (dict): LLM resolver output (after merge).
            query_names: Iterable of query names.

        Returns:
            dict: Keyed by query name; each entry has 'classic', 'llm', 'differs', 'diff'.
        """
        comparison = {}
        for name in query_names:
            c = classic.get(name, {})
            llm_entry = llm_merged.get(name, {})

            c_summary = {
                "hardDependsOn": c.get("hardDependsOn", {}),
                "softDependsOn": c.get("softDependsOn", {}),
            }
            l_summary = {
                "hardDependsOn": llm_entry.get("hardDependsOn", {}),
                "softDependsOn": llm_entry.get("softDependsOn", {}),
            }

            diff = {}
            for key in ("hardDependsOn", "softDependsOn"):
                if c_summary[key] != l_summary[key]:
                    diff[key] = {"classic": c_summary[key], "llm": l_summary[key]}

            comparison[name] = {
                "classic": c_summary,
                "llm": l_summary,
                "differs": bool(diff),
                "diff": diff,
            }
        return comparison
