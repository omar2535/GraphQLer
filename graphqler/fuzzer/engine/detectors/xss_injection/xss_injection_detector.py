from typing import Type

import requests

from .xss_injection_materializer import XSSInjectionMaterializer
from ..detector import Detector

XSS_PAYLOAD = "<script>alert(1)</script>"


class XSSInjectionDetector(Detector):
    @property
    def DETECTION_NAME(self) -> str:
        return "Cross-Site Scripting (XSS) Injection"

    @property
    def detect_only_once_for_api(self) -> bool:
        return False

    @property
    def detect_only_once_for_node(self) -> bool:
        return True

    @property
    def materializer(self) -> Type[XSSInjectionMaterializer]:
        return XSSInjectionMaterializer

    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        # Confirmed vulnerable: payload reflected verbatim in the raw HTTP response
        return request_response.status_code == 200 and XSS_PAYLOAD in request_response.text

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        if graphql_response is None:
            return False
        # Potentially vulnerable: any part of the payload reflected in the response body
        return request_response.status_code == 200 and ("<script>" in request_response.text or "alert(1)" in request_response.text)

    def _get_evidence(self, graphql_response: dict, request_response: requests.Response) -> str:
        if request_response.status_code == 200 and XSS_PAYLOAD in request_response.text:
            return "XSS payload reflected verbatim in response body"
        if request_response.status_code == 200 and "<script>" in request_response.text:
            return "partial XSS payload ('<script>') reflected in response body"
        if request_response.status_code == 200 and "alert(1)" in request_response.text:
            return "partial XSS payload ('alert(1)') reflected in response body"
        return ""
