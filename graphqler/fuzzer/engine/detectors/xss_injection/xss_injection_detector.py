from typing import Type

import requests

from .xss_injection_materializer import XSSInjectionMaterializer
from ..detector import Detector


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
        return False

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        if graphql_response is None:
            return False
        if 'data' not in graphql_response:
            return False
        if graphql_response['data'] is None:
            return False
        return "<script>alert(1)</script>" in graphql_response['data'] and request_response.status_code == 200
