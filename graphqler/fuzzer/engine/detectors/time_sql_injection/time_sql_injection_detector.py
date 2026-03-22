import time
from typing import Type

import requests

from graphqler.utils import plugins_handler
from graphqler.fuzzer.engine.types import ResultEnum, Result
from graphqler.fuzzer.engine.materializers.regular_payload_materializer import RegularPayloadMaterializer
from graphqler.utils.stats import Stats
from graphqler import config

from ..detector import Detector
from .time_sql_injection_materializer import TimeSQLInjectionMaterializer


class TimeSQLInjectionDetector(Detector):
    """Detects time-based blind SQL injection by injecting sleep payloads
    (pg_sleep / SLEEP / WAITFOR DELAY) and measuring response latency.

    To avoid false positives from naturally slow endpoints, the detector first
    sends a benign baseline request and measures its latency.  The injection
    latency is then compared as a *delta* against that baseline:

        time_delta = injection_elapsed - baseline_elapsed

    A delta >= TIME_BASED_SQL_SLEEP_SECONDS * TIME_BASED_SQL_THRESHOLD_RATIO
    is treated as confirmed time-based SQLi.  A delta >= 1 s (but below the
    confirmed threshold) is flagged as potentially vulnerable.
    """

    @property
    def DETECTION_NAME(self) -> str:
        return "Time-based SQL Injection (Blind SQLi)"

    @property
    def detect_only_once_for_api(self) -> bool:
        return False

    @property
    def detect_only_once_for_node(self) -> bool:
        return True

    @property
    def materializer(self) -> Type[TimeSQLInjectionMaterializer]:
        return TimeSQLInjectionMaterializer

    def get_payload(self) -> str:
        """Override to forward the configured sleep duration to the materializer."""
        materializer_instance = TimeSQLInjectionMaterializer(
            api=self.api,
            fail_on_hard_dependency_not_met=False,
            max_depth=3,
            sleep_seconds=config.TIME_BASED_SQL_SLEEP_SECONDS,
        )
        payload, _ = materializer_instance.get_payload(self.name, self.objects_bucket, self.graphql_type)
        return payload

    def detect(self) -> tuple[bool, bool]:
        """Override detect() to measure response time delta against a baseline."""
        # ── Step 1: baseline request with a benign payload ────────────────────
        self.baseline_time = 0.0
        try:
            benign_mat = RegularPayloadMaterializer(self.api, fail_on_hard_dependency_not_met=False)
            benign_payload, _ = benign_mat.get_payload(self.name, self.objects_bucket, self.graphql_type)
            t0 = time.monotonic()
            plugins_handler.get_request_utils().send_graphql_request(self.api.url, benign_payload)
            self.baseline_time = time.monotonic() - t0
        except (ConnectionError, TimeoutError, OSError):
            self.baseline_time = 0.0

        # ── Step 2: injection payload ──────────────────────────────────────────
        self.payload = self.get_payload()
        self.fuzzer_logger.debug(f"[Fuzzer] Time-based SQLi payload:\n{self.payload}")
        self.detector_logger.info(f"[Detector] Time-based SQLi payload:\n{self.payload}")

        start = time.monotonic()
        graphql_response, request_response = plugins_handler.get_request_utils().send_graphql_request(
            self.api.url, self.payload
        )
        self.elapsed_time = time.monotonic() - start

        # Delta removes naturally-slow-endpoint noise
        self.time_delta = max(0.0, self.elapsed_time - self.baseline_time)

        result = Result(
            result_enum=ResultEnum.GENERAL_SUCCESS,
            payload=self.payload,
            status_code=request_response.status_code,
            graphql_response=graphql_response,
            raw_response_text=request_response.text,
        )
        Stats().add_http_status_code(self.name, request_response.status_code)
        Stats().update_stats_from_result(self.node, result)

        self.detector_logger.info(
            f"[{request_response.status_code}] elapsed={self.elapsed_time:.2f}s "
            f"baseline={self.baseline_time:.2f}s delta={self.time_delta:.2f}s  "
            f"Response: {request_response.text}"
        )
        self.fuzzer_logger.info(
            f"[{request_response.status_code}] elapsed={self.elapsed_time:.2f}s "
            f"baseline={self.baseline_time:.2f}s delta={self.time_delta:.2f}s  "
            f"Response: {graphql_response}"
        )

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
        threshold = config.TIME_BASED_SQL_SLEEP_SECONDS * config.TIME_BASED_SQL_THRESHOLD_RATIO
        return self.time_delta >= threshold

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        # Flag as potential if the *delta* over baseline is noticeably high but below confirmed threshold
        return not self._is_vulnerable(graphql_response, request_response) and self.time_delta >= 1.0

    def _get_evidence(self, graphql_response: dict, request_response: requests.Response) -> str:
        threshold = config.TIME_BASED_SQL_SLEEP_SECONDS * config.TIME_BASED_SQL_THRESHOLD_RATIO
        if self.time_delta >= threshold:
            return (
                f"response delayed {self.time_delta:.2f}s above baseline "
                f"(>= {threshold:.1f}s threshold for {config.TIME_BASED_SQL_SLEEP_SECONDS}s sleep payload; "
                f"baseline={self.baseline_time:.2f}s, injection={self.elapsed_time:.2f}s)"
            )
        if self.time_delta >= 1.0:
            return (
                f"response {self.time_delta:.2f}s slower than baseline — "
                f"unusual but below confirmed threshold "
                f"(baseline={self.baseline_time:.2f}s, injection={self.elapsed_time:.2f}s)"
            )
        return ""
