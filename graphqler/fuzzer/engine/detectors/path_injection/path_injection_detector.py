from typing import Type, override

import requests

from graphqler.utils.api import API

from ...materializers.getter import Getter
from ...materializers.injection_materializer import InjectionMaterializer
from ..detector import Detector


# The main class that's being used
class PathInjectionMaterializer(InjectionMaterializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 20):
        super().__init__(api, fail_on_hard_dependency_not_met)
        self.api = api
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        self.max_depth = max_depth
        self.getter = PathInjectionGetter()


# Override the getters class to add custom getters for SQL injection
class PathInjectionGetter(Getter):
    def __init__(self):
        super().__init__()

    @override
    def get_random_string(self, input_name: str) -> str:
        return '"../../../../etc/passwd"'


class PathInjectionDetector(Detector):
    @property
    def DETECTION_NAME(self) -> str:
        return "Path Injection"

    @property
    def detect_only_once_for_api(self) -> bool:
        return False

    @property
    def detect_only_once_for_node(self) -> bool:
        return True

    @property
    def materializer(self) -> Type[PathInjectionMaterializer]:
        return PathInjectionMaterializer

    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        if graphql_response is None or 'data' not in graphql_response or graphql_response['data'] is None:
            return False
        return "root:x:0:0:root:" in request_response.text or "root:x:0:0:root:" in str(graphql_response['data'])

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        if graphql_response is None or 'data' not in graphql_response or graphql_response['data'] is None:
            return False
        return ((graphql_response['data'] is not None and "Permission denied" in request_response.text)
                or ('../../../../etc/passwd' in request_response.text))
