"""LLM-based fallback classifier for IDOR chain candidates.

Called only when:
  1. ``config.IDOR_USE_LLM_FALLBACK`` is ``True``, AND
  2. The heuristic confidence for a chain is below
     ``config.IDOR_HEURISTIC_CONFIDENCE_THRESHOLD``.

Uses the same litellm infrastructure as the LLM resolver so any provider
(OpenAI, Anthropic, Ollama, LiteLLM proxy) is supported out of the box.

Returns
-------
``(is_candidate: bool, reason: str)``
  ``is_candidate`` is ``True`` when the LLM considers the chain an IDOR test
  candidate, ``False`` otherwise.  On any error / timeout the function returns
  ``(False, "<error description>")`` so the chain is conservatively skipped.
"""

from __future__ import annotations

import json
import logging

from graphqler import config
from graphqler.chains.chain import Chain

logger = logging.getLogger(__name__)


def _get_litellm():
    try:
        import litellm  # type: ignore[import]
        return litellm
    except ImportError as exc:
        raise ImportError(
            "litellm is required for IDOR_USE_LLM_FALLBACK=True. "
            "Install it with: uv add litellm"
        ) from exc


def _describe_chain(chain: Chain, split_index: int) -> str:
    """Build a compact, human-readable description of the chain for the LLM prompt."""
    lines: list[str] = []
    for i, node in enumerate(chain.nodes):
        role = "SETUP (primary token)" if i < split_index else "TEST (secondary/attacker token)"
        node_type = node.graphql_type
        mut_type = f" [{node.mutation_type}]" if node.mutation_type else ""
        body = node.body or {}
        output_type = body.get("outputType") or body.get("output_type") or body.get("type") or "unknown"
        inputs = body.get("inputs") or body.get("parameters") or {}
        input_summary = ", ".join(f"{k}: {v.get('type', '?') if isinstance(v, dict) else v}" for k, v in list(inputs.items())[:5])
        lines.append(
            f"  [{role}] {node_type}{mut_type} '{node.name}' "
            f"→ returns '{output_type}'"
            + (f", inputs: ({input_summary})" if input_summary else "")
        )
    return "\n".join(lines)


def classify(chain: Chain, split_index: int) -> tuple[bool, str]:
    """Ask the configured LLM whether this chain is an IDOR candidate.

    Args:
        chain: The compiled chain to evaluate.
        split_index: Index of the first "test" node (as determined by the
            heuristic classifier).

    Returns:
        ``(is_candidate, reason)`` — ``is_candidate`` is ``True`` only when the
        LLM is confident the chain represents a meaningful cross-user access test.
    """
    try:
        litellm = _get_litellm()
    except ImportError as exc:
        return False, str(exc)

    chain_description = _describe_chain(chain, split_index)

    system_prompt = (
        "You are a security analyst specialising in GraphQL API vulnerabilities. "
        "You are given a GraphQL operation chain split into two parts:\n"
        "  SETUP nodes — run by the resource owner (primary token)\n"
        "  TEST nodes  — run by an attacker (secondary token) using IDs produced during SETUP\n\n"
        "Respond with JSON only, no markdown:\n"
        '{"is_idor_candidate": true/false, "reason": "<one sentence>"}\n\n'
        '"is_idor_candidate" should be true ONLY when:\n'
        "  • The SETUP creates a user-specific resource (order, profile, message, etc.), AND\n"
        "  • The TEST node tries to read or modify that resource by ID, AND\n"
        "  • A well-designed API should restrict the TEST node to the resource owner.\n"
        'Set it to false for public catalogue endpoints (products, articles, public posts).'
    )
    user_prompt = (
        f"Chain name: {chain.name}\n\n"
        f"Operations:\n{chain_description}\n\n"
        "Is this a meaningful IDOR test candidate?"
    )

    kwargs: dict = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if config.LLM_API_KEY:
        kwargs["api_key"] = config.LLM_API_KEY
    if config.LLM_BASE_URL:
        kwargs["base_url"] = config.LLM_BASE_URL

    for attempt in range(max(1, config.LLM_MAX_RETRIES)):
        try:
            response = litellm.completion(**kwargs)
            choices = getattr(response, "choices", None) or response.get("choices", [])
            content = ""
            if choices:
                message = getattr(choices[0], "message", None)
                if message is not None:
                    content = str(getattr(message, "content", "") or "")
                elif isinstance(choices[0], dict):
                    content = str((choices[0].get("message") or {}).get("content", ""))
            raw = content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            data = json.loads(raw)
            is_candidate = bool(data.get("is_idor_candidate", False))
            reason = str(data.get("reason", ""))
            return is_candidate, reason
        except json.JSONDecodeError:
            logger.debug("LLM IDOR classifier attempt %d returned non-JSON: %r", attempt + 1, content)
        except Exception as exc:
            logger.warning("LLM IDOR classifier error on attempt %d: %s", attempt + 1, exc)
            return False, f"LLM error: {exc}"

    return False, "LLM returned non-JSON after all retries"
