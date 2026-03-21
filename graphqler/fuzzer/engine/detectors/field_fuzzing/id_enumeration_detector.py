"""ID Enumeration Detector (IDOR)

Equivalent of GraphQLMap's GRAPHQL_INCREMENT_N mode:
  probes integer IDs 1 .. ID_ENUMERATION_COUNT and flags the node as potentially
  vulnerable to Insecure Direct Object Reference (IDOR) when multiple IDs return
  non-null data.

Detection logic
---------------
For each Int or ID field (first match per node):
  1. Classify the endpoint as "private", "public", or "unknown" using
     EndpointPrivacyClassifier (heuristic + optional LLM).
     - "public"  → skip (catalogue endpoints trivially return all items).
     - "unknown" → skip (conservative default to avoid false positives).
     - "private" → proceed.
  2. Send ID_ENUMERATION_COUNT requests with values 1, 2, … N.
  3. Count how many responses contain non-null data.
  4. If count >= ID_ENUMERATION_SUCCESS_THRESHOLD → flag as IDOR potential.

Flagged as *potentially* vulnerable only — a confirmed finding requires manual
verification that the objects returned belong to different owners.

Scope classification can be disabled by setting
``ID_ENUMERATION_SCOPE_HEURISTIC = False`` in config, which causes the
detector to run on every endpoint regardless of inferred scope (not
recommended — produces many false positives on public APIs).
"""

from typing import Type, override
import requests

from graphqler import config
from graphqler.utils import plugins_handler
from graphqler.utils.api import API
from graphqler.utils.objects_bucket import ObjectsBucket
from graphqler.utils.stats import Stats
from graphqler.utils.response_utils import is_non_empty_result
from graphqler.fuzzer.engine.materializers.getter import Getter
from graphqler.fuzzer.engine.materializers.regular_payload_materializer import RegularPayloadMaterializer
from graphqler.fuzzer.engine.detectors.detector import Detector
from graphqler.fuzzer.engine.detectors.field_fuzzing.endpoint_classifier import EndpointPrivacyClassifier


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_scalar_type(field_info: dict) -> str | None:
    """Walk NON_NULL / LIST wrappers until a SCALAR is reached; return its type name."""
    if field_info is None:
        return None
    if field_info.get("kind") == "SCALAR":
        return field_info.get("type")
    return _resolve_scalar_type(field_info.get("ofType"))


def collect_id_inputs(inputs: dict) -> list[str]:
    """Return field names whose resolved scalar type is Int or ID."""
    result = []
    for field_name, field_info in inputs.items():
        scalar_type = _resolve_scalar_type(field_info)
        if scalar_type in ("Int", "ID"):
            result.append(field_name)
    return result


# ── Custom getter / materializer ─────────────────────────────────────────────

class _FixedIntGetter(Getter):
    """Returns a fixed integer value for a specific field; falls back to default for all others."""

    def __init__(self, target_field: str, value: int):
        super().__init__()
        self._target = target_field
        self._value = value

    @override
    def get_random_int(self, input_name: str) -> int:
        if input_name == self._target:
            return self._value
        return super().get_random_int(input_name)

    @override
    def get_random_id(self, input_name: str, objects_bucket: ObjectsBucket) -> str:
        if input_name == self._target:
            return f'"{self._value}"'
        return super().get_random_id(input_name, objects_bucket)


class _FixedIntMaterializer(RegularPayloadMaterializer):
    def __init__(self, api: API, target_field: str = "", value: int = 0, max_depth: int = 3):
        super().__init__(api, fail_on_hard_dependency_not_met=False)
        self.max_depth = max_depth
        self.getter = _FixedIntGetter(target_field, value)


# ── Detector ──────────────────────────────────────────────────────────────────

class IDEnumerationDetector(Detector):
    """Detect IDOR / ID enumeration by probing sequential integer IDs.

    Mirrors GraphQLMap's ``GRAPHQL_INCREMENT_N`` feature in automated form.
    Controlled by config.SKIP_ENUMERATION_ATTACKS (default: True — opt-in).
    """

    @property
    def DETECTION_NAME(self) -> str:
        return "IDOR / ID Enumeration"

    @property
    def detect_only_once_for_api(self) -> bool:
        return False

    @property
    def detect_only_once_for_node(self) -> bool:
        return True

    @property
    def materializer(self) -> Type[_FixedIntMaterializer]:
        return _FixedIntMaterializer

    @override
    def detect(self) -> tuple[bool, bool]:
        if config.SKIP_ENUMERATION_ATTACKS:
            return (False, False)
        if self.graphql_type not in ("Query", "Mutation"):
            return (False, False)

        inputs = self._get_node_inputs()
        id_fields = collect_id_inputs(inputs)
        if not id_fields:
            return (False, False)

        # Scope guard: skip catalogue / public endpoints to avoid false positives.
        if config.ID_ENUMERATION_SCOPE_HEURISTIC:
            return_type_name, return_type_fields = self._get_return_type_info()
            scope = EndpointPrivacyClassifier().classify(
                self.name, return_type_name, return_type_fields
            )
            if scope != "private":
                return (False, False)

        # Use the first ID / Int field found
        target_field = id_fields[0]
        success_count, payloads_used = self._probe_ids(target_field)

        self.confirmed_vulnerable = False
        self.potentially_vulnerable = success_count >= config.ID_ENUMERATION_SUCCESS_THRESHOLD

        evidence = (
            f"{success_count}/{config.ID_ENUMERATION_COUNT} IDs (1..{config.ID_ENUMERATION_COUNT}) "
            f"returned non-null data for field '{target_field}' — possible IDOR"
            if self.potentially_vulnerable
            else ""
        )
        last_payload = payloads_used[-1] if payloads_used else ""
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

    def _get_return_type_info(self) -> tuple[str, list[str]]:
        """Return (return_type_name, list_of_field_names) for this node.

        Walks the ``output`` wrapper chain (NON_NULL → LIST → OBJECT) to find
        the concrete object type name, then looks it up in ``api.objects`` to
        collect its field names.  Falls back to empty values on any error.
        """
        try:
            if self.graphql_type == "Query":
                output = self.api.queries[self.name].get("output", {})
            else:
                output = self.api.mutations[self.name].get("output", {})

            # Walk wrapper kinds until OBJECT is found
            node = output
            type_name = ""
            while node:
                if node.get("kind") == "OBJECT":
                    type_name = node.get("name") or node.get("type") or ""
                    break
                node = node.get("ofType")

            if not type_name:
                return ("", [])

            object_def = self.api.objects.get(type_name, {})
            fields = [f["name"] for f in object_def.get("fields", []) if "name" in f]
            return (type_name, fields)
        except (KeyError, AttributeError, TypeError):
            return ("", [])

    def _get_node_inputs(self) -> dict:
        try:
            if self.graphql_type == "Query":
                return self.api.queries[self.name].get("inputs", {})
            return self.api.mutations[self.name].get("inputs", {})
        except (KeyError, AttributeError):
            return {}

    def _probe_ids(self, field_name: str) -> tuple[int, list[str]]:
        """Send ID_ENUMERATION_COUNT requests; return (success_count, list_of_payloads)."""
        success_count = 0
        payloads_used: list[str] = []

        for i in range(1, config.ID_ENUMERATION_COUNT + 1):
            mat = _FixedIntMaterializer(api=self.api, target_field=field_name, value=i, max_depth=3)
            try:
                payload, _ = mat.get_payload(self.name, self.objects_bucket, self.graphql_type)
            except Exception:
                continue

            payloads_used.append(payload)
            try:
                graphql_response, request_response = plugins_handler.get_request_utils().send_graphql_request(
                    self.api.url, payload
                )
                Stats().add_http_status_code(self.name, request_response.status_code)
                if request_response.status_code == 200 and isinstance(graphql_response.get("data"), dict):
                    data = graphql_response["data"]
                    field_result = data.get(self.name)

                    is_hit = (
                        is_non_empty_result(field_result)
                        if self.name in data
                        else any(is_non_empty_result(v) for v in data.values())
                    )
                    if is_hit:
                        success_count += 1
            except Exception:
                pass

        return success_count, payloads_used

    # Not used (detect() is fully overridden) but required by ABC
    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        raise NotImplementedError

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        raise NotImplementedError
