"""LLM-backed mutation resolver.

Resolves mutationType + hardDependsOn + softDependsOn for every mutation by
asking an LLM for its interpretation of the schema, then merging that result
with the classic ID-based resolver output.

The `.comparison` attribute (set after `resolve()`) holds the side-by-side diff
between the LLM result and the classic result for systematic analysis.
"""

import json
import copy
import logging

from graphqler import config
from graphqler.compiler.resolvers.mutation_object_resolver import MutationObjectResolver
from .llm_resolver import LLMResolver
from .prompt_templates import MUTATION_SYSTEM_PROMPT, MUTATION_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class LLMMutationObjectResolver(LLMResolver):
    """Resolves mutations using an LLM, with optional fallback to the classic resolver."""

    def __init__(self):
        super().__init__()
        self.comparison: dict = {}  # populated by resolve(); keyed by mutation name

    def resolve(self, objects: dict, mutations: dict, input_objects: dict) -> dict:
        """Resolve mutations via LLM, falling back to classic resolver on failure.

        Args:
            objects (dict): Compiled objects.
            mutations (dict): Raw parsed mutations.
            input_objects (dict): Raw parsed input objects.

        Returns:
            dict: Mutations enriched with mutationType, hardDependsOn, softDependsOn.
        """
        # Always run classic resolver — used as fallback and for comparison
        classic_mutations = MutationObjectResolver().resolve(objects, copy.deepcopy(mutations), input_objects)

        try:
            llm_raw = self._call_llm_for_mutations(objects, mutations)
            llm_validated = self.validate_llm_mutation_result(llm_raw, list(mutations.keys()), objects)
            merged = self.merge_with_classic(llm_validated, classic_mutations, list(mutations.keys()))
            self.comparison = self._build_comparison(classic_mutations, merged, mutations.keys())
            logger.info(f"LLM mutation resolver: resolved {len(llm_validated)}/{len(mutations)} mutations")
            return merged
        except Exception as exc:
            if config.LLM_RESOLVER_FALLBACK_TO_ID:
                logger.warning(f"LLM mutation resolver failed ({exc}), falling back to classic resolver")
                self.comparison = {}
                return classic_mutations
            raise

    def _call_llm_for_mutations(self, objects: dict, mutations: dict) -> dict:
        """Build the prompt and call the LLM.

        Args:
            objects (dict): Compiled objects (for schema context).
            mutations (dict): Raw parsed mutations.

        Returns:
            dict: Raw parsed JSON response from the LLM.
        """
        schema_context = self.build_schema_context(objects)
        simplified = self.simplify_endpoints(mutations)
        mutations_json = json.dumps(simplified, indent=2)

        user_prompt = MUTATION_USER_PROMPT_TEMPLATE.format(
            schema_context=schema_context,
            mutations_json=mutations_json,
        )
        return self.call_llm(MUTATION_SYSTEM_PROMPT, user_prompt)

    def _build_comparison(self, classic: dict, llm_merged: dict, mutation_names) -> dict:
        """Build a per-mutation comparison dict.

        Args:
            classic (dict): Classic resolver output.
            llm_merged (dict): LLM resolver output (after merge).
            mutation_names: Iterable of mutation names.

        Returns:
            dict: Keyed by mutation name; each entry has 'classic', 'llm', 'differs', 'diff'.
        """
        comparison = {}
        for name in mutation_names:
            c = classic.get(name, {})
            llm_entry = llm_merged.get(name, {})

            c_summary = {
                "mutationType": c.get("mutationType", "UNKNOWN"),
                "hardDependsOn": c.get("hardDependsOn", {}),
                "softDependsOn": c.get("softDependsOn", {}),
            }
            l_summary = {
                "mutationType": llm_entry.get("mutationType", "UNKNOWN"),
                "hardDependsOn": llm_entry.get("hardDependsOn", {}),
                "softDependsOn": llm_entry.get("softDependsOn", {}),
            }

            diff = {}
            for key in ("mutationType", "hardDependsOn", "softDependsOn"):
                if c_summary[key] != l_summary[key]:
                    diff[key] = {"classic": c_summary[key], "llm": l_summary[key]}

            comparison[name] = {
                "classic": c_summary,
                "llm": l_summary,
                "differs": bool(diff),
                "diff": diff,
            }
        return comparison
