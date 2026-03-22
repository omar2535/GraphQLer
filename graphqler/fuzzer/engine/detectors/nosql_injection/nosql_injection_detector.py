from typing import Type, override

import requests

from graphqler import config
from graphqler.utils import plugins_handler
from graphqler.utils.stats import Stats
from graphqler.fuzzer.engine.types import ResultEnum, Result
from graphqler.fuzzer.engine.materializers.regular_payload_materializer import RegularPayloadMaterializer

from ..detector import Detector
from .nosql_injection_materializer import NoSQLInjectionMaterializer
from .blind_nosql_extractor import BlindNoSQLExtractor


# MongoDB-style operator injection payloads
NOSQL_INJECTION_STRINGS = [
    '"{$gt: \\"\\"}"',
    '"{$ne: null}"',
    '"{$regex: \\".*\\"}"',
    '"{$where: \\"1==1\\"}"',
    '"{$exists: true}"',
    '"{$nin: []}"',
    "\"' || '1'=='1\"",
    "\"; sleep(5000); var dummy=\"",
]

# Error messages commonly emitted by NoSQL databases (MongoDB, etc.)
NOSQL_ERROR_PATTERNS = [
    "casterror",
    "mongoerror",
    "mongo",
    "bson",
    "objectid",
    "e11000",                      # MongoDB duplicate key error
    "bad query",
    "not valid json",
    "$where",
    "failed to parse",
    "unknown operator",
    "invalid operator",
    "queryfailederror",
    "mongoparseerror",
    "cannot apply $",
    "invalid use of $",
]


class NoSQLInjectionDetector(Detector):
    @property
    def DETECTION_NAME(self) -> str:
        return "NoSQL Injection (NoSQLi)"

    @property
    def detect_only_once_for_api(self) -> bool:
        return False

    @property
    def detect_only_once_for_node(self) -> bool:
        return True

    @property
    def materializer(self) -> Type[NoSQLInjectionMaterializer]:
        return NoSQLInjectionMaterializer

    @override
    def detect(self) -> tuple[bool, bool]:
        """Override to establish a benign baseline before injection.

        The blind-injection check in ``_is_potentially_vulnerable`` requires
        that a benign payload returns *no* data while the operator payload
        does — this strongly suggests the operator bypassed a filter or auth
        check.  Without a baseline we cannot tell whether data was always
        present (parameterised query, no injection) or appeared only after
        injection.
        """
        # ── Step 1: benign baseline ───────────────────────────────────────────
        self.baseline_has_data: bool = True  # conservative default
        try:
            benign_mat = RegularPayloadMaterializer(self.api, fail_on_hard_dependency_not_met=False)
            benign_payload, _ = benign_mat.get_payload(self.name, self.objects_bucket, self.graphql_type)
            baseline_gql, _ = plugins_handler.get_request_utils().send_graphql_request(
                self.api.url, benign_payload
            )
            if baseline_gql and isinstance(baseline_gql.get("data"), dict):
                self.baseline_has_data = any(v is not None for v in baseline_gql["data"].values())
            else:
                self.baseline_has_data = False
        except (ConnectionError, TimeoutError, OSError, KeyError, AttributeError):
            self.baseline_has_data = True  # assume baseline has data → blind check skipped

        # ── Step 2: injection payload (standard flow) ─────────────────────────
        self.payload = self.get_payload()
        graphql_response, request_response = plugins_handler.get_request_utils().send_graphql_request(
            self.api.url, self.payload
        )

        result = Result(
            result_enum=ResultEnum.GENERAL_SUCCESS,
            payload=self.payload,
            status_code=request_response.status_code,
            graphql_response=graphql_response,
            raw_response_text=request_response.text,
        )
        Stats().add_http_status_code(self.name, request_response.status_code)
        Stats().update_stats_from_result(self.node, result)

        self._parse_response(graphql_response, request_response)
        evidence = self._get_evidence(graphql_response, request_response)
        Stats().add_vulnerability(
            self.DETECTION_NAME,
            self.name,
            self.confirmed_vulnerable,
            self.potentially_vulnerable,
            payload=self.payload,
            evidence=evidence,
        )
        return (self.confirmed_vulnerable, self.potentially_vulnerable)

    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        response_text_lower = request_response.text.lower()
        return any(pattern in response_text_lower for pattern in NOSQL_ERROR_PATTERNS)

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        if graphql_response is None or "data" not in graphql_response:
            return False
        if request_response.status_code != 200:
            return False
        if not any(kw in self.payload for kw in NOSQL_INJECTION_STRINGS):
            return False
        injection_has_data = isinstance(graphql_response.get("data"), dict) and any(
            v is not None for v in graphql_response["data"].values()
        )
        # Only flag when the operator payload produces data that the benign
        # baseline did NOT — a strong signal that the operator bypassed a filter.
        return injection_has_data and not self.baseline_has_data

    def _get_evidence(self, graphql_response: dict, request_response: requests.Response) -> str:
        response_text_lower = request_response.text.lower()
        for pattern in NOSQL_ERROR_PATTERNS:
            if pattern in response_text_lower:
                return f"matched NoSQL error pattern: '{pattern}'"
        if self._is_potentially_vulnerable(graphql_response, request_response):
            evidence = (
                "NoSQL operator payload returned data when benign baseline returned none "
                "(potential filter/auth bypass)"
            )
            if config.NOSQLI_BLIND_EXTRACTION:
                extracted = BlindNoSQLExtractor(self.api.url, self.payload).extract()
                if extracted:
                    evidence += f"; blind extraction recovered value: '{extracted}'"
            return evidence
        return ""
