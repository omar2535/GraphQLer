from typing import Type, override

import requests
import random

from graphqler.utils.api import API

from ...materializers.getter import Getter
from ...materializers.injection_materializer import InjectionMaterializer
from ..detector import Detector


SQL_INJECTION_STRINGS = [
    '"aaa \' OR 1=1--"',
    '"\' OR \'1\'=\'1"',
    '"1; DROP TABLE users--"',
    '"1\' UNION SELECT null,null,null--"',
    '"1\' AND SLEEP(3)--"',
    '"\' OR 1=1 LIMIT 1--"',
    '"admin\'--"',
    '"1\' AND 1=CONVERT(int, (SELECT TOP 1 table_name FROM information_schema.tables))--"',
]

# Error messages commonly emitted by SQL databases that indicate injection success
SQL_ERROR_PATTERNS = [
    "syntax error",
    "you have an error in your sql syntax",
    "unclosed quotation mark",
    "quoted string not properly terminated",
    "ora-",
    "pg_query",
    "mysql_fetch",
    "sqlite_",
    "sqlstate",
    "jdbc",
    "odbc",
    "invalid query",
    "sql syntax",
    "unexpected token",
    "unterminated string",
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
        if input_name in ['filter', 'search', 'query', 'name', 'username', 'password', 'email', 'id', 'text', 'message', 'input', 'value']:
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
        response_text_lower = request_response.text.lower()
        return any(pattern in response_text_lower for pattern in SQL_ERROR_PATTERNS)

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        if graphql_response is None or 'data' not in graphql_response or graphql_response['data'] is None:
            return False
        # Flag if the server returned data successfully on an injection payload (possible blind SQLi)
        if request_response.status_code == 200 and graphql_response['data'] and any(keyword in self.payload for keyword in SQL_INJECTION_STRINGS):
            return True
        return False
