from typing import Type

import requests

from .introspection_materializer import IntrospectionMaterializer
from ..detector import Detector


class IntrospectionDetector(Detector):
    """OSCommandInjectionDetector
    Will have two main functions:
    first will be the materializer to use
    second will be the detection function on both the payload and the response
    If the malicious payload is detected in the response, the detector will return the vulnerability
    """
    @property
    def DETECTION_NAME(self) -> str:
        return "Introspection Enabled"

    @property
    def detect_only_once_for_api(self) -> bool:
        return True

    @property
    def detect_only_once_for_node(self) -> bool:
        return True

    @property
    def materializer(self) -> Type[IntrospectionMaterializer]:
        return IntrospectionMaterializer

    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        return "__schema" in graphql_response['data'] and request_response.status_code == 200

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        return self._is_vulnerable(graphql_response, request_response)
