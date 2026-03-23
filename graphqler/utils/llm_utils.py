"""Shared LLM utility — single entry point for all litellm calls in GraphQLer.

Every module that needs to talk to an LLM (dependency resolver, IDOR classifier,
endpoint privacy classifier, vulnerability reporter, …) should call
``call_llm()`` from here instead of wiring litellm themselves.  This keeps the
retry loop, JSON extraction, and provider configuration in one place.
"""

from __future__ import annotations

import json
import logging

from graphqler import config

logger = logging.getLogger(__name__)


# ── litellm lazy import ───────────────────────────────────────────────────────

def _get_litellm():
    """Import and return litellm only when an LLM call is actually made."""
    try:
        import litellm  # type: ignore[import]
        return litellm
    except ImportError as exc:
        raise ImportError(
            "litellm is required for LLM features. Install it with: uv add litellm"
        ) from exc


# ── JSON extraction ───────────────────────────────────────────────────────────

def _extract_json_from_text(text: str) -> dict:
    """Extract a JSON object from text that may be wrapped in markdown fences or prose.

    Tries in order:
    1. Strip a leading ``` / ```json fence and trailing ```, then parse.
    2. Direct ``json.loads`` on the stripped text.
    3. Slice from the first ``{`` to the last ``}`` and parse.

    Args:
        text (str): Raw text returned by the LLM.

    Returns:
        dict: Parsed JSON object.

    Raises:
        ValueError: If no valid JSON object can be extracted.
    """
    text = text.strip()

    if text.startswith("```"):
        end_of_first_line = text.find("\n")
        if end_of_first_line != -1:
            text = text[end_of_first_line + 1:]
        if text.endswith("```"):
            text = text[:-3].rstrip()
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start: end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from LLM response: {text[:300]}")


# ── JSON mode support detection ───────────────────────────────────────────────

def _supports_json_mode() -> bool:
    """Return True if the configured model supports the ``format`` JSON mode option.

    Handles both prefixed (``openai/gpt-4o-mini``) and unprefixed
    (``gpt-4o-mini``) model strings.
    """
    llm_model = config.LLM_MODEL
    if "/" in llm_model:
        provider, model = llm_model.split("/", 1)
    else:
        provider = "openai"
        model = llm_model

    if not model:
        model = llm_model
        provider = "openai"

    litellm = _get_litellm()
    return litellm.supports_response_schema(model=model, custom_llm_provider=provider)


# ── Core call ─────────────────────────────────────────────────────────────────

def call_llm(system_prompt: str, user_prompt: str) -> dict:
    """Send a prompt pair to the configured LLM and return parsed JSON.

    Uses litellm so any provider (OpenAI, Anthropic, Ollama, LiteLLM proxy)
    works transparently — just set ``LLM_MODEL`` / ``LLM_BASE_URL`` in config.

    Behaviour:
    * If the model supports JSON mode the ``format`` hint is passed.
    * If the response cannot be parsed as JSON, retries up to
      ``LLM_MAX_RETRIES`` times, appending a correction turn that asks the
      model to produce raw JSON only.

    Args:
        system_prompt (str): System-role message.
        user_prompt (str): User-role message.

    Returns:
        dict: Parsed JSON from the LLM response.

    Raises:
        ImportError: If litellm is not installed.
        ValueError: If the LLM returns malformed JSON after all retries.
        Exception: Any litellm / network error propagates to the caller.
    """
    litellm = _get_litellm()

    base_kwargs: dict = {"model": config.LLM_MODEL}
    if config.LLM_API_KEY:
        base_kwargs["api_key"] = config.LLM_API_KEY
    if config.LLM_BASE_URL:
        base_kwargs["base_url"] = config.LLM_BASE_URL
    if _supports_json_mode():
        base_kwargs["format"] = "json"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    max_attempts = config.LLM_MAX_RETRIES + 1
    last_error: Exception | None = None

    for attempt in range(max_attempts):
        logger.info(
            "Calling LLM (%s) (attempt %d/%d) …",
            config.LLM_MODEL, attempt + 1, max_attempts,
        )
        response = litellm.completion(**{**base_kwargs, "messages": messages})
        raw: str = response.choices[0].message.content or ""

        try:
            return _extract_json_from_text(raw)
        except ValueError as exc:
            last_error = exc
            logger.warning("LLM returned non-JSON on attempt %d: %s", attempt + 1, raw[:200])
            if attempt < max_attempts - 1:
                messages = messages + [
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": (
                            "Your previous response was not valid JSON. "
                            "Please respond with ONLY a valid JSON object — "
                            "no markdown, no code fences, no explanation, just the raw JSON."
                        ),
                    },
                ]

    raise ValueError(
        f"LLM returned non-JSON after {max_attempts} attempt(s): {last_error}"
    ) from last_error
