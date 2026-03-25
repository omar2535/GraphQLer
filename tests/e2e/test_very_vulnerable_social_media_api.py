"""End-to-end test for the Very Vulnerable Social Media API.

Validates that GraphQLer's UAF (use-after-delete) chain detection identifies
the ``getPost`` endpoint as a UAF candidate — meaning it still returns data
for posts that have been deleted via ``deletePost``.

Test flow
---------
1. Start the Flask API server on a dedicated port.
2. Run GraphQLer's compile phase (introspection, dependency graph, chain gen).
3. Run GraphQLer's fuzz phase (executes chains including UAF candidates).
4. Assert that a ``UAF_CHAIN`` vulnerability was flagged in the stats report.
5. Assert that the expected detection output files were written.
"""

import os
import shutil

from graphqler import __main__, config
from tests.e2e.utils.run_api import run_python_project, wait_for_server
from tests.e2e.utils.base import GraphQLerIntegrationTestCase
from tests.e2e.utils.stats import (
    get_vulnerabilities_from_stats,
    is_detection_flagged,
)


class TestVeryVulnerableSocialMediaApi(GraphQLerIntegrationTestCase):
    PORT = 4009
    URL = f"http://localhost:{PORT}/graphql"
    PATH = "ci-test-very-vulnerable-social-media-api/"
    API_PATH = "sample-graphql-apis/very-vulnerable-social-media-api"
    CONFIG_PATH = "sample-graphql-apis/test_configs/very_vulnerable_social_media_api_config.toml"
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

    def test_compile_generates_uaf_chain_file(self):
        """The compiler should emit a uaf.yml chain file when a CREATE→DELETE→ACCESS pattern exists."""
        self._compile()
        uaf_chain_path = os.path.join(self.PATH, config.CHAINS_DIR_NAME, "uaf.yml")
        self.assertTrue(
            os.path.exists(uaf_chain_path),
            f"Expected uaf.yml chain file at {uaf_chain_path}",
        )
        self.assertGreater(os.path.getsize(uaf_chain_path), 0)

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
        self.assertTrue(
            os.path.exists(detections_path),
            "detections/ directory should be created after fuzzing",
        )

    # ── UAF detection ─────────────────────────────────────────────────────────

    def _run_and_get_vulns(self) -> dict:
        self._compile()
        self._fuzz()
        return get_vulnerabilities_from_stats(self.PATH)

    def test_uaf_chain_detected(self):
        """GraphQLer must flag UAF_CHAIN as potentially vulnerable for getPost."""
        vulns = self._run_and_get_vulns()
        self.assertTrue(
            is_detection_flagged(vulns, "UAF_CHAIN"),
            f"Expected UAF_CHAIN to be flagged as potentially vulnerable. Got: {vulns}",
        )

    def test_uaf_detection_node_is_get_post(self):
        """The UAF detection should be tied to the getPost operation."""
        vulns = self._run_and_get_vulns()
        uaf_vulns = vulns.get("UAF_CHAIN", {})
        self.assertTrue(len(uaf_vulns) > 0, "Expected at least one UAF_CHAIN entry")
        # At least one entry should reference the 'getPost' node (camelCase from Graphene)
        found = any("post" in node_name.lower() for node_name in uaf_vulns)
        self.assertTrue(found, f"Expected a post-related UAF detection. Got nodes: {list(uaf_vulns.keys())}")

    def test_uaf_detection_files_written(self):
        """Each UAF detection should produce raw_log.txt and summary.txt."""
        self._run_and_get_vulns()
        detections_root = os.path.join(self.PATH, config.DETECTIONS_DIR_NAME, "UAF_CHAIN")
        self.assertTrue(
            os.path.isdir(detections_root),
            f"Expected detections/UAF_CHAIN/ directory under {self.PATH}",
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
        self.assertTrue(found_pair, "Expected at least one UAF detection to have raw_log.txt and summary.txt")

    def test_uaf_summary_contains_chain_and_payload(self):
        """summary.txt should include chain steps and the triggering payload."""
        self._run_and_get_vulns()
        detections_root = os.path.join(self.PATH, config.DETECTIONS_DIR_NAME, "UAF_CHAIN")
        self.assertTrue(os.path.isdir(detections_root))

        for node_dir in os.listdir(detections_root):
            summary_path = os.path.join(detections_root, node_dir, "summary.txt")
            if os.path.exists(summary_path):
                with open(summary_path) as f:
                    content = f.read()
                self.assertIn("=== Chain ===", content)
                self.assertIn("=== Final Payload ===", content)
                self.assertIn("=== Final Response", content)
                return

        self.fail("No summary.txt found in any UAF detection directory")
