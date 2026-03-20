from typing import Type

import requests

from .ssrf_injection_materialilzer import SSRFInjectionMaterializer
from ..detector import Detector

# Response patterns that may indicate internal service data leakage via SSRF
SSRF_RESPONSE_PATTERNS = [
    "connection refused",
    "no route to host",
    "failed to connect",
    "could not connect",
    "open(): permission denied",
    "operation not permitted",
    "network is unreachable",
    # AWS/GCP/Azure metadata service indicators
    "ami-id",
    "instance-id",
    "169.254.169.254",
    "metadata.google.internal",
]


class SSRFInjectionDetector(Detector):
    @property
    def DETECTION_NAME(self) -> str:
        return "SSRF Injection"

    @property
    def detect_only_once_for_api(self) -> bool:
        return False

    @property
    def detect_only_once_for_node(self) -> bool:
        return True

    @property
    def materializer(self) -> Type[SSRFInjectionMaterializer]:
        return SSRFInjectionMaterializer

    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        response_text_lower = request_response.text.lower()
        return any(pattern in response_text_lower for pattern in SSRF_RESPONSE_PATTERNS)

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        if graphql_response is None:
            return False
        # A 200 with data on SSRF-like inputs suggests the server may be making outbound requests
        ssrf_input_keywords = ['"http://', '"https://', '"localhost', '"127.0.0.1', '"0.0.0.0']
        if request_response.status_code == 200 and graphql_response.get('data') and any(kw in self.payload for kw in ssrf_input_keywords):
            return True
        return False

    def _get_evidence(self, graphql_response: dict, request_response: requests.Response) -> str:
        response_text_lower = request_response.text.lower()
        for pattern in SSRF_RESPONSE_PATTERNS:
            if pattern in response_text_lower:
                return f"matched SSRF indicator: '{pattern}'"
        if self._is_potentially_vulnerable(graphql_response, request_response):
            return "server returned data on SSRF-like URL input (potential blind SSRF)"
        return ""
