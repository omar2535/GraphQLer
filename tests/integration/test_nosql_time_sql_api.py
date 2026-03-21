"""Integration tests for the nosql-time-sql-api.

Verifies that GraphQLer's injection detectors correctly flag the intentionally
vulnerable endpoints exposed by tests/test-apis/nosql-time-sql-api/.

Detectors exercised:
  - NoSQL Injection       (searchUsers — MongoDB-operator bypass / MongoServerError)
  - Time-based SQL Injection (timeSqlQuery — SLEEP / pg_sleep / WAITFOR DELAY)
"""

import os
import shutil
import unittest

from graphqler import __main__, config
from tests.integration.utils.run_api import run_node_project, wait_for_server
from tests.integration.utils.stats import (
    get_vulnerabilities_from_stats,
    is_detection_flagged,
)


class TestNoSQLTimeSQLAPI(unittest.TestCase):
    PORT = 4005
    URL = f"http://localhost:{PORT}/graphql"
    PATH = "ci-test-nosql-time-sql-api/"
    API_PATH = "tests/test-apis/nosql-time-sql-api"
    CONFIG_PATH = "tests/test-apis/test_configs/nosql_time_sql_api_config.toml"
    process = None
    process_pid = None

    @classmethod
    def setUpClass(cls):
        cls.process = run_node_project(cls.API_PATH, [], str(cls.PORT))
        cls.process_pid = cls.process.pid

        parsed = __main__.parse_config(cls.CONFIG_PATH)
        __main__.set_config(parsed)

        wait_for_server(cls.URL, timeout=30)

    @classmethod
    def tearDownClass(cls):
        if cls.process and cls.process.pid == cls.process_pid:
            cls.process.kill()
            cls.process.wait()
        if os.path.exists(cls.PATH):
            shutil.rmtree(cls.PATH)

    # ── Compilation ──────────────────────────────────────────────────────────

    def test_compile_generates_introspection_file(self):
        __main__.run_compile_mode(self.PATH, self.URL)
        introspection_path = os.path.join(self.PATH, config.INTROSPECTION_RESULT_FILE_NAME)
        self.assertTrue(os.path.exists(introspection_path))
        self.assertGreater(os.path.getsize(introspection_path), 0)

    # ── Fuzzing ──────────────────────────────────────────────────────────────

    def test_fuzz_generates_stats_file(self):
        __main__.run_compile_mode(self.PATH, self.URL)
        __main__.run_fuzz_mode(self.PATH, self.URL)
        stats_path = os.path.join(self.PATH, config.STATS_FILE_NAME)
        self.assertTrue(os.path.exists(stats_path))
        self.assertGreater(os.path.getsize(stats_path), 0)

    # ── Injection detection ───────────────────────────────────────────────────

    _cached_vulns = None

    def _run_and_get_vulns(self):
        if self.__class__._cached_vulns is None:
            __main__.run_compile_mode(self.PATH, self.URL)
            __main__.run_fuzz_mode(self.PATH, self.URL)
            self.__class__._cached_vulns = get_vulnerabilities_from_stats(self.PATH)
        return self.__class__._cached_vulns

    def test_nosql_injection_detected(self):
        vulns = self._run_and_get_vulns()
        self.assertTrue(
            is_detection_flagged(vulns, "NoSQL Injection (NoSQLi)"),
            f"Expected NoSQL injection to be flagged. Got: {vulns}",
        )

    def test_time_based_sql_injection_detected(self):
        vulns = self._run_and_get_vulns()
        self.assertTrue(
            is_detection_flagged(vulns, "Time-based SQL Injection (Blind SQLi)"),
            f"Expected time-based SQL injection to be flagged. Got: {vulns}",
        )

    def test_time_based_sql_injection_confirmed(self):
        """The time delay must be long enough that the detector confirms (not just flags) the vuln."""
        vulns = self._run_and_get_vulns()
        self.assertTrue(
            is_detection_flagged(vulns, "Time-based SQL Injection (Blind SQLi)", confirmed=True),
            f"Expected time-based SQL injection to be *confirmed*. Got: {vulns}",
        )
