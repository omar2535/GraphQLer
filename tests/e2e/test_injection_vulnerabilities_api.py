"""Integration tests for the injection-vulnerabilities-api.

Verifies that GraphQLer's injection detectors correctly flag the intentionally
vulnerable endpoints exposed by sample-graphql-apis/injection-vulnerabilities-api/.

Detectors exercised:
  - SQL Injection   (searchPosts — raw string interpolated into SQLite query)
  - XSS Injection   (createPost / getPost — content reflected verbatim)
  - Path Injection  (readFile — path traversal to /etc/passwd)
  - OS Command Injection (executeCommand — shell passthrough)
"""

import os
import shutil

from graphqler import __main__, config
from tests.e2e.utils.run_api import run_node_project, wait_for_server
from tests.e2e.utils.base import GraphQLerIntegrationTestCase
from tests.e2e.utils.stats import (
    get_vulnerabilities_from_stats,
    is_detection_flagged,
)


class TestInjectionVulnerabilitiesAPI(GraphQLerIntegrationTestCase):
    PORT = 4002
    URL = f"http://localhost:{PORT}/graphql"
    PATH = "ci-test-injection-vulnerabilities-api/"
    API_PATH = "sample-graphql-apis/injection-vulnerabilities-api"
    CONFIG_PATH = "sample-graphql-apis/test_configs/injection_vulnerabilities_api_config.toml"
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
        self._compile()
        introspection_path = os.path.join(self.PATH, config.INTROSPECTION_RESULT_FILE_NAME)
        self.assertTrue(os.path.exists(introspection_path))
        self.assertGreater(os.path.getsize(introspection_path), 0)

    # ── Fuzzing ──────────────────────────────────────────────────────────────

    def test_fuzz_generates_stats_file(self):
        self._compile()
        self._fuzz()
        stats_path = os.path.join(self.PATH, config.STATS_FILE_NAME)
        self.assertTrue(os.path.exists(stats_path))
        self.assertGreater(os.path.getsize(stats_path), 0)

    def test_fuzz_generates_json_stats_file(self):
        self._compile()
        self._fuzz()
        json_path = os.path.join(self.PATH, "stats.json")
        self.assertTrue(os.path.exists(json_path))
        self.assertGreater(os.path.getsize(json_path), 0)

    # ── Injection detection ───────────────────────────────────────────────────

    def _run_and_get_vulns(self):
        self._compile()
        self._fuzz()
        return get_vulnerabilities_from_stats(self.PATH)

    def test_sql_injection_detected(self):
        vulns = self._run_and_get_vulns()
        self.assertTrue(
            is_detection_flagged(vulns, "SQL Injection (SQLi) Injection"),
            f"Expected SQL injection to be flagged. Got: {vulns}",
        )

    def test_xss_injection_detected(self):
        vulns = self._run_and_get_vulns()
        self.assertTrue(
            is_detection_flagged(vulns, "Cross-Site Scripting (XSS) Injection"),
            f"Expected XSS to be flagged. Got: {vulns}",
        )

    def test_path_injection_detected(self):
        vulns = self._run_and_get_vulns()
        self.assertTrue(
            is_detection_flagged(vulns, "Path Injection"),
            f"Expected path injection to be flagged. Got: {vulns}",
        )

    def test_os_command_injection_detected(self):
        vulns = self._run_and_get_vulns()
        self.assertTrue(
            is_detection_flagged(vulns, "OS Command Injection"),
            f"Expected OS command injection to be flagged. Got: {vulns}",
        )
