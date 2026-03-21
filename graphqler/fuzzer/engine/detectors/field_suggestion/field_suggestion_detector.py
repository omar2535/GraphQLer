import random
from typing import Type

import requests

from graphqler.utils import plugins_handler
from graphqler.utils.stats import Stats
from .field_suggestion_materializer import FieldSuggestionMaterializer
from ..detector import Detector


class FieldSuggestionsDetector(Detector):
    """Field Suggestions Detector

    Iterates over all known query names (shuffled) and sends each as a
    misspelled field name.  Detection succeeds as soon as any response
    contains a "did you mean" hint, making the result independent of which
    individual query name happens to be blocked by a deny-list.
    """

    @property
    def DETECTION_NAME(self) -> str:
        return "Field Suggestions Enabled"

    @property
    def detect_only_once_for_api(self) -> bool:
        return True

    @property
    def detect_only_once_for_node(self) -> bool:
        return True

    @property
    def materializer(self) -> Type[FieldSuggestionMaterializer]:
        return FieldSuggestionMaterializer

    # ── multi-query detect override ──────────────────────────────────────────

    def detect(self) -> tuple[bool, bool]:
        query_names = list(self.api.queries.keys())
        random.shuffle(query_names)

        for query_name in query_names:
            misspelled = query_name + "abc"
            payload = f"query {{\n  {misspelled} {{\n    id\n  }}\n}}"

            graphql_response, request_response = (
                plugins_handler.get_request_utils().send_graphql_request(
                    self.api.url, payload
                )
            )
            Stats().add_http_status_code(self.name, request_response.status_code)

            if self._is_vulnerable(graphql_response, request_response):
                self.payload = payload
                self.confirmed_vulnerable = True
                self.potentially_vulnerable = True
                evidence = self._get_evidence(graphql_response, request_response)
                Stats().add_vulnerability(
                    self.DETECTION_NAME,
                    self.name,
                    self.confirmed_vulnerable,
                    self.potentially_vulnerable,
                    payload=payload,
                    evidence=evidence,
                )
                self.detector_logger.info(
                    f"Detector {self.DETECTION_NAME} finished detecting - "
                    f"is_vulnerable: True - potentially_vulnerable: True"
                )
                return (True, True)

        self.detector_logger.info(
            f"Detector {self.DETECTION_NAME} finished detecting - "
            f"is_vulnerable: False - potentially_vulnerable: False"
        )
        Stats().add_vulnerability(
            self.DETECTION_NAME,
            self.name,
            False,
            False,
            payload="",
            evidence="",
        )
        return (False, False)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        errors = graphql_response.get("errors") or []
        if errors and "did you mean" in str(errors[0].get("message", "")).lower():
            return True
        return "did you mean" in request_response.text.lower()

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        return self._is_vulnerable(graphql_response, request_response)

    def _get_evidence(self, graphql_response: dict, request_response: requests.Response) -> str:
        if self._is_vulnerable(graphql_response, request_response):
            return "server returned a field suggestion ('did you mean') — field enumeration is possible"
        return ""
