from typing import Type, override

import requests
import random

from graphqler.utils.api import API

from ...materializers.getter import Getter
from ...materializers.injection_materializer import InjectionMaterializer
from ..detector import Detector


SQL_INJECTION_STRINGS = [
    '"aaa \' OR 1=1--"',
]


class SQLInjectionMaterializer(InjectionMaterializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 20):
        super().__init__(api, fail_on_hard_dependency_not_met)
        self.api = api
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        self.getter = SQLInjectionGetter()


class SQLInjectionGetter(Getter):
    def __init__(self):
        super().__init__()

    @override
    def get_random_string(self, input_name: str) -> str:
        if input_name in ['filter', 'search', 'query', 'name', 'username', 'password', 'email', 'id']:
            injection_str = random.choice(SQL_INJECTION_STRINGS)
            return injection_str
        else:
            return super().get_random_string(input_name)


# The main class that's being used
class SQLInjectionDetector(Detector):
    @property
    def DETECTION_NAME(self) -> str:
        return "SQL Injection (SQLi) Injection"

    @property
    def detect_only_once_for_api(self) -> bool:
        return False

    @property
    def detect_only_once_for_node(self) -> bool:
        return True

    @property
    def materializer(self) -> Type[SQLInjectionMaterializer]:
        return SQLInjectionMaterializer

    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        return False

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        # Initial check to see if the response is empty
        if graphql_response is None or 'data' not in graphql_response or graphql_response['data'] is None:
            return False
        if request_response.status_code == 200 and graphql_response['data'] and any(keyword in self.payload for keyword in SQL_INJECTION_STRINGS):
            return True
        else:
            return False
