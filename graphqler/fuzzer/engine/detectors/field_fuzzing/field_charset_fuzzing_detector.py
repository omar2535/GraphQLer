"""Field Charset Fuzzing Detector

Explanation:
  iterates every character in a configurable charset over String input fields
  and flags the node as potentially vulnerable to blind data extraction when the
  response length varies significantly between characters.
  
  This is like time-based blind SQLi but with response length as the oracle instead of time.

Detection logic
---------------
For each String field (up to MAX_CHARSET_FUZZ_FIELDS per node):
  1. Send one request per character in FIELD_CHARSET.
  2. Record the response text length for each.
  3. Compute relative spread:  (max_len - min_len) / avg_len
  4. If spread > FIELD_RESPONSE_LENGTH_VARIANCE_THRESHOLD → field is enumerable.

This is flagged as *potentially* vulnerable only — confirmed vulnerability requires
a manual follow-up (the detector cannot tell *why* the lengths differ).
"""

from typing import Type, override
import requests

from graphqler import config
from graphqler.utils import plugins_handler
from graphqler.utils.api import API
from graphqler.utils.stats import Stats
from graphqler.fuzzer.engine.materializers.getter import Getter
from graphqler.fuzzer.engine.materializers.regular_payload_materializer import RegularPayloadMaterializer
from graphqler.fuzzer.engine.detectors.detector import Detector


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_scalar_type(field_info: dict | None) -> str | None:
    """Walk NON_NULL / LIST wrappers until a SCALAR is reached; return its type name."""
    if field_info is None:
        return None
    if field_info.get("kind") == "SCALAR":
        return field_info.get("type")
    return _resolve_scalar_type(field_info.get("ofType"))


def collect_string_inputs(inputs: dict) -> list[str]:
    """Return field names whose resolved scalar type is String."""
    result = []
    for field_name, field_info in inputs.items():
        if _resolve_scalar_type(field_info) == "String":
            result.append(field_name)
    return result


# ── Custom getter / materializer ─────────────────────────────────────────────

class _FixedStringGetter(Getter):
    """Returns a fixed value for a specific field; falls back to default for all others."""

    def __init__(self, target_field: str, value: str):
        super().__init__()
        self._target = target_field
        self._value = value

    @override
    def get_random_string(self, input_name: str) -> str:
        if input_name == self._target:
            return f'"{self._value}"'
        return super().get_random_string(input_name)


class _FixedStringMaterializer(RegularPayloadMaterializer):
    def __init__(self, api: API, target_field: str = "", value: str = "", max_depth: int = 3):
        super().__init__(api, fail_on_hard_dependency_not_met=False)
        self.max_depth = max_depth
        self.getter = _FixedStringGetter(target_field, value)


# ── Detector ──────────────────────────────────────────────────────────────────

class FieldCharsetFuzzingDetector(Detector):
    """Detect blind field enumeration by charset-fuzzing String inputs.

    Mirrors GraphQLMap's ``GRAPHQL_CHARSET`` feature in automated form.
    Controlled by config.SKIP_ENUMERATION_ATTACKS (default: True — opt-in).
    """

    @property
    def DETECTION_NAME(self) -> str:
        return "Field Charset Enumeration (Blind Data Extraction)"

    @property
    def detect_only_once_for_api(self) -> bool:
        return False

    @property
    def detect_only_once_for_node(self) -> bool:
        return True

    @property
    def materializer(self) -> Type[_FixedStringMaterializer]:
        return _FixedStringMaterializer

    @override
    def detect(self) -> tuple[bool, bool]:
        if config.SKIP_ENUMERATION_ATTACKS:
            return (False, False)
        if self.graphql_type not in ("Query", "Mutation"):
            return (False, False)

        inputs = self._get_node_inputs()
        string_fields = collect_string_inputs(inputs)
        if not string_fields:
            return (False, False)

        enumerable_fields: list[str] = []
        for field_name in string_fields[: config.MAX_CHARSET_FUZZ_FIELDS]:
            if self._field_shows_variance(field_name):
                enumerable_fields.append(field_name)

        self.confirmed_vulnerable = False
        self.potentially_vulnerable = bool(enumerable_fields)

        last_payload = self._build_payload(string_fields[0], config.FIELD_CHARSET[0]) if string_fields else ""
        evidence = (
            f"response length varies across charset for field(s): {enumerable_fields}"
            if enumerable_fields
            else ""
        )
        Stats().add_vulnerability(
            self.DETECTION_NAME,
            self.name,
            self.confirmed_vulnerable,
            self.potentially_vulnerable,
            payload=last_payload,
            evidence=evidence,
        )
        return (self.confirmed_vulnerable, self.potentially_vulnerable)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_node_inputs(self) -> dict:
        try:
            if self.graphql_type == "Query":
                return self.api.queries[self.name].get("inputs", {})
            return self.api.mutations[self.name].get("inputs", {})
        except (KeyError, AttributeError):
            return {}

    def _build_payload(self, field_name: str, value: str) -> str:
        mat = _FixedStringMaterializer(api=self.api, target_field=field_name, value=value, max_depth=3)
        try:
            payload, _ = mat.get_payload(self.name, self.objects_bucket, self.graphql_type)
        except Exception:
            payload = ""
        return payload

    def _get_response_length(self, field_name: str, value: str) -> int:
        payload = self._build_payload(field_name, value)
        if not payload:
            return 0
        try:
            _, request_response = plugins_handler.get_request_utils().send_graphql_request(
                self.api.url, payload
            )
            Stats().add_http_status_code(self.name, request_response.status_code)
            return len(request_response.text)
        except Exception:
            return 0

    def _field_shows_variance(self, field_name: str) -> bool:
        lengths = [self._get_response_length(field_name, char) for char in config.FIELD_CHARSET]
        non_zero = [x for x in lengths if x > 0]
        if len(non_zero) < 2:
            return False
        max_len = max(non_zero)
        min_len = min(non_zero)
        avg_len = sum(non_zero) / len(non_zero)
        if avg_len == 0:
            return False
        # TODO: extract _resolve_scalar_type() into a shared helper module and reuse it
        # here and in id_enumeration_detector.py to keep scalar unwrapping consistent.
        spread = (max_len - min_len) / avg_len
        if spread <= config.FIELD_RESPONSE_LENGTH_VARIANCE_THRESHOLD:
            return False
        # Require that at least some responses are much shorter than average —
        # this distinguishes a boolean oracle (some chars match, others don't) from a
        # search API that returns different *counts* of records (all non-zero, but varying
        # in size).  A genuine blind oracle will have near-empty responses for non-matching
        # characters.
        near_empty_fraction = sum(1 for length in non_zero if length < avg_len * 0.3) / len(non_zero)
        return near_empty_fraction >= 0.1

    # Not used (detect() is fully overridden) but required by ABC
    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        raise NotImplementedError

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        raise NotImplementedError
