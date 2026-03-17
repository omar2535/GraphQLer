"""Integration tests for the api-security-api.

Verifies that GraphQLer's API-level security detectors correctly flag the
intentionally misconfigured endpoints in tests/test-apis/api-security-api/.

Detectors exercised:
  - Introspection Enabled   (Apollo Server started with introspection: true)
  - Field Suggestions Enabled (Apollo Server returns "Did you mean…" hints)
  - Query Deny Bypass        (middleware blocks `adminUsers` by name but not
                               by alias: `s: adminUsers`)
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


class TestAPISecurityAPI(unittest.TestCase):
    PORT = 4004
    URL = f"http://localhost:{PORT}/graphql"
    PATH = "ci-test-api-security-api/"
    API_PATH = "tests/test-apis/api-security-api"
    CONFIG_PATH = "tests/test-apis/test_configs/api_security_api_config.toml"
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

    def test_fuzz_generates_json_stats_file(self):
        __main__.run_compile_mode(self.PATH, self.URL)
        __main__.run_fuzz_mode(self.PATH, self.URL)
        json_path = os.path.join(self.PATH, "stats.json")
        self.assertTrue(os.path.exists(json_path))
        self.assertGreater(os.path.getsize(json_path), 0)

    # ── Security detection ────────────────────────────────────────────────────

    def _run_and_get_vulns(self):
        __main__.run_compile_mode(self.PATH, self.URL)
        __main__.run_fuzz_mode(self.PATH, self.URL)
        return get_vulnerabilities_from_stats(self.PATH)

    def test_introspection_enabled_detected(self):
        vulns = self._run_and_get_vulns()
        self.assertTrue(
            is_detection_flagged(vulns, "Introspection Enabled"),
            f"Expected introspection-enabled to be flagged. Got: {vulns}",
        )

    def test_field_suggestions_enabled_detected(self):
        vulns = self._run_and_get_vulns()
        self.assertTrue(
            is_detection_flagged(vulns, "Field Suggestions Enabled"),
            f"Expected field-suggestions-enabled to be flagged. Got: {vulns}",
        )

    def test_query_deny_bypass_detected(self):
        vulns = self._run_and_get_vulns()
        self.assertTrue(
            is_detection_flagged(vulns, "Query deny bypass"),
            f"Expected query-deny-bypass to be flagged. Got: {vulns}",
        )
