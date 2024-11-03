from typing import Type

import requests

from ..materializers.injection import OSCommandInjectionMaterializer
from .detector import Detector


class OSCommandInjectionDetector(Detector):
    """OSCommandInjectionDetector
    Will have two main functions:
    first will be the materializer to use
    second will be the detection function on both the payload and the response
    If the malicious payload is detected in the response, the detector will return the vulnerability
    """
    @property
    def DETECTION_NAME(self) -> str:
        return "os_command_injection"

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
        return "root:x:0:0:root:" in request_response.text
