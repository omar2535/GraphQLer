"""LLMResolver — base class for LLM-backed dependency resolvers.

Responsibilities:
  1. Build a compact, token-efficient schema context string from the objects dict.
  2. Convert raw parsed mutations/queries into a simplified JSON representation
     that is easier for an LLM to process.
  3. Call the LLM via litellm (supports OpenAI, Anthropic, Ollama, LiteLLM proxy,
     and any other provider supported by litellm out of the box).
  4. Parse and validate the structured JSON response.
  5. Fall back to the classic ID-based resolver on any failure when
     LLM_RESOLVER_FALLBACK_TO_ID is True.
"""

import json
import logging
from graphqler import config
try:
    import litellm  # noqa: PLC0415 — lazy import so litellm is optional
except ImportError as exc:
    raise ImportError("litellm is required for USE_LLM=True. Install it with: uv add litellm") from exc

logger = logging.getLogger(__name__)


class LLMResolver:
    """Base class — subclasses implement `resolve()` and call the helpers here."""

    # ── Schema context ────────────────────────────────────────────────────────

    def build_schema_context(self, objects: dict) -> str:
        """Return a compact, human-readable description of all objects.

        Example output line:
            User: id(ID!), email(String!), name(String), posts([Post])

        Args:
            objects (dict): Compiled objects dict from ObjectListParser.

        Returns:
            str: Multi-line string, one object per line.
        """
        lines = ["Available GraphQL objects in this API:"]
        for obj_name, obj_body in objects.items():
            fields = obj_body.get("fields", [])
            field_strs = []
            for f in fields:
                type_str = self._field_type_str(f)
                field_strs.append(f"{f['name']}({type_str})")
            lines.append(f"  {obj_name}: {', '.join(field_strs) if field_strs else '(no fields)'}")
        return "\n".join(lines)

    def _field_type_str(self, field: dict) -> str:
        """Convert a field's kind/ofType structure to a compact type string like 'String!', '[Post]'."""
        kind = field.get("kind", "")
        name = field.get("type") or field.get("name") or ""
        oftype = field.get("ofType")

        if kind == "NON_NULL":
            inner = self._oftype_str(oftype) if oftype else name
            return f"{inner}!"
        elif kind == "LIST":
            inner = self._oftype_str(oftype) if oftype else name
            return f"[{inner}]"
        else:
            return name or kind

    def _oftype_str(self, oftype: dict) -> str:
        if oftype is None:
            return ""
        kind = oftype.get("kind", "")
        name = oftype.get("name") or oftype.get("type") or ""
        inner = oftype.get("ofType")
        if kind == "NON_NULL":
            return f"{self._oftype_str(inner)}!" if inner else f"{name}!"
        elif kind == "LIST":
            return f"[{self._oftype_str(inner)}]" if inner else f"[{name}]"
        else:
            return name or kind

    # ── Simplified endpoint representations ──────────────────────────────────

    def simplify_endpoints(self, endpoints: dict) -> dict:
        """Convert raw parsed endpoints to a compact dict suitable for LLM prompts.

        The simplified form replaces the nested ofType structures with readable
        type strings like "String!", "ID!", "[Post]".

        Args:
            endpoints (dict): Raw queries or mutations from the parser.

        Returns:
            dict: Simplified representation keyed by endpoint name.
        """
        simplified = {}
        for name, body in endpoints.items():
            inputs = {}
            for input_name, input_body in (body.get("inputs") or {}).items():
                inputs[input_name] = self._input_type_str(input_body)

            output_type = self._oftype_str(body.get("output")) if body.get("output") else ""
            simplified[name] = {
                "description": body.get("description") or "",
                "inputs": inputs,
                "output": output_type,
            }
        return simplified

    def _input_type_str(self, input_body: dict) -> str:
        """Return a readable type string for an input, e.g. 'ID!', 'String', '[String!]'."""
        kind = input_body.get("kind", "")
        oftype = input_body.get("ofType")
        if kind == "NON_NULL":
            inner = self._oftype_str(oftype) if oftype else ""
            return f"{inner}!"
        elif kind == "LIST":
            inner = self._oftype_str(oftype) if oftype else ""
            return f"[{inner}]"
        else:
            type_name = input_body.get("type") or input_body.get("name") or kind
            return type_name

    # ── LLM call ─────────────────────────────────────────────────────────────

    def _supports_json_mode(self) -> bool:
        """Return True if the configured model supports response_format json_object."""
        provider = config.LLM_MODEL.split("/")[0].lower()
        model = config.LLM_MODEL.lower()
        does_support_json = litellm.supports_response_schema(model=model, custom_llm_provider=provider)
        return does_support_json

    def _extract_json_from_text(self, text: str) -> dict:
        """Extract a JSON object from text that may be wrapped in markdown fences or prose.

        Tries in order:
        1. Strip a leading ``` / ```json fence and trailing ``` then parse.
        2. Direct json.loads on the stripped text.
        3. Slice from the first '{' to the last '}' and parse.

        Raises:
            ValueError: If no valid JSON object can be extracted.
        """
        text = text.strip()

        # Strip markdown code fences (```json ... ``` or ``` ... ```)
        if text.startswith("```"):
            end_of_first_line = text.find("\n")
            if end_of_first_line != -1:
                text = text[end_of_first_line + 1 :]
            if text.endswith("```"):
                text = text[:-3].rstrip()
            text = text.strip()

        # Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Find the outermost JSON object by scanning for first '{' … last '}'
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not extract valid JSON from LLM response: {text[:300]}")

    def call_llm(self, system_prompt: str, user_prompt: str) -> dict:
        """Send a prompt to the configured LLM and return parsed JSON.

        Uses litellm so any provider (OpenAI, Anthropic, Ollama, LiteLLM proxy)
        works transparently — just change LLM_MODEL / LLM_BASE_URL in config.

        * response_format is only passed for models that support JSON mode.
        * If the response cannot be parsed as JSON, retries up to LLM_MAX_RETRIES
          times, appending a correction turn asking for JSON-only output.

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

        base_kwargs: dict = {
            "model": config.LLM_MODEL,
        }
        if config.LLM_API_KEY:
            base_kwargs["api_key"] = config.LLM_API_KEY
        if config.LLM_BASE_URL:
            base_kwargs["base_url"] = config.LLM_BASE_URL
        if self._supports_json_mode():
            base_kwargs["format"] = 'json'

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        last_error: Exception | None = None
        max_attempts = config.LLM_MAX_RETRIES + 1

        for attempt in range(max_attempts):
            logger.info(f"Calling LLM ({config.LLM_MODEL}) for dependency resolution (attempt {attempt + 1}/{max_attempts}) …")
            response = litellm.completion(**{**base_kwargs, "messages": messages})
            raw = response.choices[0].message.content or ""

            try:
                return self._extract_json_from_text(raw)
            except ValueError as exc:
                last_error = exc
                logger.warning(f"LLM returned non-JSON on attempt {attempt + 1}: {raw[:200]}")
                if attempt < max_attempts - 1:
                    # Append a correction turn so the model sees its own bad output
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

        raise ValueError(f"LLM returned non-JSON after {max_attempts} attempt(s): {last_error}") from last_error

    # ── Result merging ────────────────────────────────────────────────────────

    def merge_with_classic(self, llm_result: dict, classic_result: dict, endpoint_names: list[str]) -> dict:
        """Merge LLM result with classic result.

        LLM result is authoritative for endpoints it returns.
        Classic result fills in any endpoints the LLM omitted.

        Args:
            llm_result (dict): Structured output from the LLM (validated).
            classic_result (dict): Output from the classic resolver.
            endpoint_names (list[str]): All endpoint names to ensure complete coverage.

        Returns:
            dict: Merged result with all endpoints populated.
        """
        import copy
        merged = copy.deepcopy(classic_result)
        for name in endpoint_names:
            if name in llm_result:
                llm_entry = llm_result[name]
                merged[name]["hardDependsOn"] = llm_entry.get("hardDependsOn", {})
                merged[name]["softDependsOn"] = llm_entry.get("softDependsOn", {})
                if "mutationType" in llm_entry:
                    merged[name]["mutationType"] = llm_entry["mutationType"]
        return merged

    # ── Validation ────────────────────────────────────────────────────────────

    def validate_llm_mutation_result(self, raw: dict, endpoint_names: list[str], objects: dict) -> dict:
        """Validate and clean the LLM response for mutations.

        - Removes entries for unknown endpoint names (hallucinations)
        - Removes dependency values that are not known object names
        - Falls back to "UNKNOWN" mutationType when missing

        Args:
            raw (dict): Raw parsed JSON from the LLM.
            endpoint_names (list[str]): Valid mutation names.
            objects (dict): Valid object names.

        Returns:
            dict: Cleaned result.
        """
        valid = {}
        known_endpoints = set(endpoint_names)
        known_objects = set(objects.keys())
        for name, entry in raw.items():
            if name not in known_endpoints:
                logger.debug(f"LLM hallucinated unknown mutation '{name}', skipping")
                continue
            valid[name] = {
                "mutationType": entry.get("mutationType", "UNKNOWN") if entry.get("mutationType") in ("CREATE", "UPDATE", "DELETE", "UNKNOWN") else "UNKNOWN",
                "hardDependsOn": {k: v for k, v in entry.get("hardDependsOn", {}).items() if v in known_objects},
                "softDependsOn": {k: v for k, v in entry.get("softDependsOn", {}).items() if v in known_objects},
            }
        return valid

    def validate_llm_query_result(self, raw: dict, endpoint_names: list[str], objects: dict) -> dict:
        """Validate and clean the LLM response for queries.

        Args:
            raw (dict): Raw parsed JSON from the LLM.
            endpoint_names (list[str]): Valid query names.
            objects (dict): Valid object names.

        Returns:
            dict: Cleaned result.
        """
        valid = {}
        known_endpoints = set(endpoint_names)
        known_objects = set(objects.keys())
        for name, entry in raw.items():
            if name not in known_endpoints:
                logger.debug(f"LLM hallucinated unknown query '{name}', skipping")
                continue
            valid[name] = {
                "hardDependsOn": {k: v for k, v in entry.get("hardDependsOn", {}).items() if v in known_objects},
                "softDependsOn": {k: v for k, v in entry.get("softDependsOn", {}).items() if v in known_objects},
            }
        return valid
