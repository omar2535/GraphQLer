from typing import Type

import requests

from .ssrf_injection_materialilzer import SSRFInjectionMaterializer
from ..detector import Detector


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
        return False

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        """
        A potentially vulnerable API to SSRF is one that returns a 200 status code when given improper inputs for the hostname / port variables
        """
        keywords = ["http", "localhost", "3000"]
        if request_response.status_code == 200 and self.payload != "" and any(keyword in self.payload for keyword in keywords):
            return True
        else:
            return False
