"""ID Enumeration Detector (IDOR)

Equivalent of GraphQLMap's GRAPHQL_INCREMENT_N mode:
  probes integer IDs 1 .. ID_ENUMERATION_COUNT and flags the node as potentially
  vulnerable to Insecure Direct Object Reference (IDOR) when multiple IDs return
  non-null data.

Detection logic
---------------
For each Int or ID field (first match per node):
  1. Send ID_ENUMERATION_COUNT requests with values 1, 2, … N.
  2. Count how many responses contain non-null data.
  3. If count >= ID_ENUMERATION_SUCCESS_THRESHOLD → flag as IDOR potential.

Flagged as *potentially* vulnerable only — a confirmed finding requires manual
verification that the objects returned belong to different owners.
"""

from typing import Type, override
import requests

from graphqler import config
from graphqler.utils import plugins_handler
from graphqler.utils.api import API
from graphqler.utils.objects_bucket import ObjectsBucket
from graphqler.utils.stats import Stats
from graphqler.fuzzer.engine.materializers.getter import Getter
from graphqler.fuzzer.engine.materializers.regular_payload_materializer import RegularPayloadMaterializer
from graphqler.fuzzer.engine.detectors.detector import Detector


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
                    if any(v is not None for v in graphql_response["data"].values()):
                        success_count += 1
            except Exception:
                pass

        return success_count, payloads_used

    # Not used (detect() is fully overridden) but required by ABC
    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        raise NotImplementedError

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        raise NotImplementedError
