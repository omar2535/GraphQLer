import os
import shutil

from graphqler import __main__, config
from tests.e2e.utils.run_api import run_python_project, wait_for_server
from tests.e2e.utils.base import GraphQLerIntegrationTestCase
from tests.e2e.utils.stats import (
    get_vulnerabilities_from_stats,
    is_detection_flagged,
)


class TestIDORApi(GraphQLerIntegrationTestCase):
    PORT = 4006
    URL = f"http://localhost:{PORT}/graphql"
    PATH = "ci-test-idor-api/"
    API_PATH = "sample-graphql-apis/idor-api"
    CONFIG_PATH = "sample-graphql-apis/test_configs/idor_api_config.toml"
    process = None
    process_pid = None

    @classmethod
    def setUpClass(cls):
        cls.process = run_python_project(cls.API_PATH, str(cls.PORT))
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

    # ── Compilation ───────────────────────────────────────────────────────────

    def test_compile_generates_introspection_file(self):
        self._compile()
        introspection_path = os.path.join(self.PATH, config.INTROSPECTION_RESULT_FILE_NAME)
        self.assertTrue(os.path.exists(introspection_path))
        self.assertGreater(os.path.getsize(introspection_path), 0)

    # ── Fuzzing ───────────────────────────────────────────────────────────────

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

    def test_fuzz_generates_detections_directory(self):
        self._compile()
        self._fuzz()
        detections_path = os.path.join(self.PATH, config.DETECTIONS_DIR_NAME)
        self.assertTrue(os.path.exists(detections_path), "detections/ directory should be created")

    # ── IDOR detection ────────────────────────────────────────────────────────

    def _run_and_get_vulns(self):
        self._compile()
        self._fuzz()
        return get_vulnerabilities_from_stats(self.PATH)

    def test_idor_chain_detected(self):
        vulns = self._run_and_get_vulns()
        self.assertTrue(
            is_detection_flagged(vulns, "IDOR_CHAIN", confirmed=True),
            f"Expected IDOR_CHAIN to be confirmed. Got: {vulns}",
        )

    def test_idor_detection_files_written(self):
        """Each IDOR detection should produce raw_log.txt and summary.txt."""
        self._run_and_get_vulns()
        detections_root = os.path.join(self.PATH, config.DETECTIONS_DIR_NAME, "IDOR_CHAIN")
        self.assertTrue(
            os.path.isdir(detections_root),
            f"Expected detections/IDOR_CHAIN/ directory under {self.PATH}",
        )
        found_pair = False
        for node_dir in os.listdir(detections_root):
            node_path = os.path.join(detections_root, node_dir)
            if os.path.isdir(node_path):
                raw_log = os.path.join(node_path, "raw_log.txt")
                summary = os.path.join(node_path, "summary.txt")
                if os.path.exists(raw_log) and os.path.exists(summary):
                    found_pair = True
                    break
        self.assertTrue(found_pair, "Expected at least one IDOR detection to have raw_log.txt and summary.txt")

    def test_idor_summary_contains_chain_and_payload(self):
        """summary.txt should include chain steps and the triggering payload."""
        self._run_and_get_vulns()
        detections_root = os.path.join(self.PATH, config.DETECTIONS_DIR_NAME, "IDOR_CHAIN")
        self.assertTrue(os.path.isdir(detections_root))

        for node_dir in os.listdir(detections_root):
            summary_path = os.path.join(detections_root, node_dir, "summary.txt")
            if os.path.exists(summary_path):
                content = open(summary_path).read()
                self.assertIn("=== Chain ===", content)
                self.assertIn("=== Final Payload ===", content)
                self.assertIn("=== Final Response", content)
                return

        self.fail("No summary.txt found in any IDOR detection directory")
