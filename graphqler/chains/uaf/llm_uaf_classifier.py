"""LLM-based fallback classifier for UAF chain candidates.

Called only when:
  1. ``config.UAF_USE_LLM_FALLBACK`` is ``True``, AND
  2. The heuristic confidence for a chain is below
     ``config.UAF_HEURISTIC_CONFIDENCE_THRESHOLD``.

Uses ``graphqler.utils.llm_utils.call_llm()`` so any provider configured in
``config`` (OpenAI, Anthropic, Ollama, LiteLLM proxy) is supported out of the box.

Returns
-------
``(is_candidate: bool, reason: str)``
  ``is_candidate`` is ``True`` when the LLM considers the chain a UAF test
  candidate, ``False`` otherwise.  On any error / timeout the function returns
  ``(False, "<error description>")`` so the chain is conservatively skipped.
"""

from __future__ import annotations

import logging

from graphqler.chains.chain import Chain
from graphqler.chains.uaf.prompt_templates import UAF_SYSTEM_PROMPT, UAF_USER_PROMPT_TEMPLATE
from graphqler.utils import llm_utils

logger = logging.getLogger(__name__)


def _describe_chain(chain: Chain, split_index: int) -> str:
    """Build a compact, human-readable description of the chain for the LLM prompt."""
    lines: list[str] = []
    for i, step in enumerate(chain.steps):
        role = "SETUP (create then delete)" if i < split_index else "POST-DELETE (access after deletion)"
        node = step.node
        node_type = node.graphql_type
        mut_type = f" [{node.mutation_type}]" if node.mutation_type else ""
        body = node.body or {}
        output_type = body.get("outputType") or body.get("output_type") or body.get("type") or "unknown"
        inputs = body.get("inputs") or body.get("parameters") or {}
        input_summary = ", ".join(
            f"{k}: {v.get('type', '?') if isinstance(v, dict) else v}"
            for k, v in list(inputs.items())[:5]
        )
        lines.append(
            f"  [{role}] {node_type}{mut_type} '{node.name}' "
            f"→ returns '{output_type}'"
            + (f", inputs: ({input_summary})" if input_summary else "")
        )
    return "\n".join(lines)


def classify(chain: Chain, split_index: int) -> tuple[bool, str]:
    """Ask the configured LLM whether this chain is a UAF candidate.

    Args:
        chain: The compiled chain to evaluate.
        split_index: Index of the first post-delete node (as determined by the
            heuristic classifier).

    Returns:
        ``(is_candidate, reason)`` — ``is_candidate`` is ``True`` only when the
        LLM is confident the chain represents a meaningful use-after-delete test.
    """
    chain_description = _describe_chain(chain, split_index)
    user_prompt = UAF_USER_PROMPT_TEMPLATE.format(
        chain_name=chain.name,
        chain_description=chain_description,
    )

    try:
        data = llm_utils.call_llm(UAF_SYSTEM_PROMPT, user_prompt)
        is_candidate = bool(data.get("is_uaf_candidate", False))
        reason = str(data.get("reason", ""))
        return is_candidate, reason
    except Exception as exc:
        logger.warning("LLM UAF classifier error: %s", exc)
        return False, f"LLM error: {exc}"
