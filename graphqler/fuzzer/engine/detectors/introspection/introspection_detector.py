from typing import Type

import requests

from .introspection_materializer import IntrospectionMaterializer
from ..detector import Detector


class IntrospectionDetector(Detector):
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
        if graphql_response is None:
            return False
        if 'errors' in graphql_response:
            return False
        return "__schema" in graphql_response['data'] and request_response.status_code == 200

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        return self._is_vulnerable(graphql_response, request_response)
