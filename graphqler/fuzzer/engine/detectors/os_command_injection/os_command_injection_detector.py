from typing import Type

import requests

from .os_command_injection_materializer import OSCommandInjectionMaterializer
from ..detector import Detector


class OSCommandInjectionDetector(Detector):
    """OSCommandInjectionDetector
    Will have two main functions:
    first will be the materializer to use
    second will be the detection function on both the payload and the response
    If the malicious payload is detected in the response, the detector will return the vulnerability
    """
    @property
    def DETECTION_NAME(self) -> str:
        return "OS Command Injection"

    @property
    def detect_only_once_for_api(self) -> bool:
        return False

    @property
    def detect_only_once_for_node(self) -> bool:
        return True

    @property
    def materializer(self) -> Type[OSCommandInjectionMaterializer]:
        return OSCommandInjectionMaterializer

    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        if graphql_response is None or 'data' not in graphql_response or graphql_response['data'] is None:
            return False
        return "root:x:0:0:root:" in request_response.text or "root:x:0:0:root:" in str(graphql_response['data'])

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        return self._is_vulnerable(graphql_response, request_response)
