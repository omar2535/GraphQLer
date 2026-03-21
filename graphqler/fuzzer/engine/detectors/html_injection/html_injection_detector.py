from typing import Type, override

import requests

from graphqler.fuzzer.engine.detectors.detector import Detector
from graphqler.fuzzer.engine.materializers.getter import Getter
from graphqler.fuzzer.engine.materializers.injection_materializer import InjectionMaterializer
from graphqler.utils.api import API


# The main class that's being used
class HTMLInjectionMaterializer(InjectionMaterializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 20):
        super().__init__(api, fail_on_hard_dependency_not_met)
        self.api = api
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        self.max_depth = max_depth
        self.getter = HTMLInjectionGetter()


# Override the getters class to add custom getters for SQL injection
class HTMLInjectionGetter(Getter):
    def __init__(self):
        super().__init__()

    @override
    def get_random_string(self, input_name: str) -> str:
        return '"<h1>Hello world!</h1>"'


class HTMLInjectionDetector(Detector):
    @property
    def DETECTION_NAME(self) -> str:
        return "HTML Injection"

    @property
    def detect_only_once_for_api(self) -> bool:
        return False

    @property
    def detect_only_once_for_node(self) -> bool:
        return True

    @property
    def materializer(self) -> Type[HTMLInjectionMaterializer]:
        return HTMLInjectionMaterializer

    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        return False

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        # Only flag when the server actually *reflects* the HTML payload in the response body,
        # not merely when it returns HTTP 200 with data (which any field accepting strings would do).
        html_payload = "<h1>Hello world!</h1>"
        return request_response.status_code == 200 and html_payload in request_response.text

    def _get_evidence(self, graphql_response: dict, request_response: requests.Response) -> str:
        if self._is_potentially_vulnerable(graphql_response, request_response):
            return "HTML payload <h1>Hello world!</h1> reflected in server response — potential HTML/XSS injection"
        return ""
