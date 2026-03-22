"""Integration tests for GraphQLer CLI modes.

Each test invokes ``python -m graphqler`` as a subprocess so that:
- singletons (Stats, FEngine, ObjectsBucket) are fully isolated per test
- config module state cannot leak between tests
- the real CLI argument-parsing / dispatch path is exercised end-to-end

All tests share a single food-delivery-api server started in ``setUpClass``.
Each test gets its own output directory that is deleted in ``tearDown``.
"""

import os
import shutil
import subprocess
import unittest

from tests.e2e.utils.run_api import run_node_project, wait_for_server

# Use a port that does not clash with any e2e test server (all use 4000-4008).
PORT = 4020
URL = f"http://localhost:{PORT}/graphql"
API_PATH = "sample-graphql-apis/food-delivery-api"


def _run_cli(path: str, mode: str, url: str | None = None, extra_args: list[str] | None = None) -> subprocess.CompletedProcess:
    """Invoke ``python -m graphqler`` and return the completed process."""
    cmd = ["uv", "run", "python", "-m", "graphqler", "--mode", mode, "--path", path]
    if url:
        cmd += ["--url", url]
    if extra_args:
        cmd += extra_args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=180)


class TestCLIModes(unittest.TestCase):
    """Test each CLI mode and the sequences between them."""

    process = None
    process_pid = None

    # ── server lifecycle ──────────────────────────────────────────────────────

    @classmethod
    def setUpClass(cls):
        node_cmd = shutil.which("node")
        cls.process = run_node_project(
            API_PATH,
            [f"{node_cmd} dbinitializer.js"],
            str(PORT),
        )
        cls.process_pid = cls.process.pid
        ready = wait_for_server(URL, timeout=30)
        if not ready:
            cls.process.kill()
            raise RuntimeError(f"Food-delivery API failed to start on port {PORT}")

    @classmethod
    def tearDownClass(cls):
        if cls.process and cls.process.pid == cls.process_pid:
            cls.process.kill()
            cls.process.wait()

    # ── per-test output directory ─────────────────────────────────────────────

    def setUp(self):
        self.path = f"ci-test-cli-{self._testMethodName}/"
        os.makedirs(self.path, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _compile(self, extra_args: list[str] | None = None) -> subprocess.CompletedProcess:
        return _run_cli(self.path, "compile", URL, extra_args)

    def _compile_graph(self) -> subprocess.CompletedProcess:
        return _run_cli(self.path, "compile-graph", URL)

    def _compile_chains(self) -> subprocess.CompletedProcess:
        # compile-chains does not require --url
        return _run_cli(self.path, "compile-chains")

    def _fuzz(self) -> subprocess.CompletedProcess:
        return _run_cli(self.path, "fuzz", URL)

    def _run(self) -> subprocess.CompletedProcess:
        return _run_cli(self.path, "run", URL)

    def _assert_compiled_graph(self):
        """Assert that compile-graph output files exist."""
        self.assertTrue(
            os.path.exists(os.path.join(self.path, "introspection_result.json")),
            "introspection_result.json missing",
        )
        self.assertTrue(
            os.path.exists(os.path.join(self.path, "compiled", "compiled_objects.yml")),
            "compiled_objects.yml missing",
        )
        self.assertTrue(
            os.path.exists(os.path.join(self.path, "compiled", "compiled_queries.yml")),
            "compiled_queries.yml missing",
        )

    def _assert_chains_exist(self):
        """Assert that at least one chains YAML was generated."""
        chains_dir = os.path.join(self.path, "compiled", "chains")
        self.assertTrue(os.path.isdir(chains_dir), "compiled/chains/ directory missing")
        chain_files = [f for f in os.listdir(chains_dir) if f.endswith(".yml")]
        self.assertGreater(len(chain_files), 0, "No chain YAML files generated")

    def _assert_fuzz_output(self):
        """Assert that fuzzing produced a stats file and a fuzzer log."""
        self.assertTrue(
            os.path.exists(os.path.join(self.path, "stats.txt")),
            "stats.txt missing after fuzz",
        )
        self.assertTrue(
            os.path.exists(os.path.join(self.path, "logs", "fuzzer.log")),
            "logs/fuzzer.log missing after fuzz",
        )

    # ── compile-graph mode ────────────────────────────────────────────────────

    def test_compile_graph_mode_creates_introspection_and_compiled_files(self):
        """compile-graph creates schema files but does NOT produce chains."""
        result = self._compile_graph()
        self.assertEqual(result.returncode, 0, f"compile-graph failed:\n{result.stderr}")
        self._assert_compiled_graph()

    def test_compile_graph_mode_does_not_create_chains(self):
        """compile-graph deliberately stops before chain generation."""
        self._compile_graph()
        chains_dir = os.path.join(self.path, "compiled", "chains")
        # chains dir should be absent (or, if created empty, contain no yml files)
        if os.path.isdir(chains_dir):
            chain_files = [f for f in os.listdir(chains_dir) if f.endswith(".yml")]
            self.assertEqual(
                len(chain_files), 0,
                "compile-graph should not generate chain YAML files",
            )

    # ── compile-chains mode ───────────────────────────────────────────────────

    def test_compile_chains_after_compile_graph_creates_chains(self):
        """compile-chains (run after compile-graph) produces chain YAML files."""
        self._compile_graph()
        result = self._compile_chains()
        self.assertEqual(result.returncode, 0, f"compile-chains failed:\n{result.stderr}")
        self._assert_chains_exist()

    def test_compile_chains_on_empty_directory_exits_cleanly(self):
        """compile-chains with no prior graph handles an empty graph without crashing."""
        result = self._compile_chains()
        # Should exit 0 (it prints a warning and returns early, not sys.exit(1))
        self.assertEqual(result.returncode, 0, f"compile-chains crashed:\n{result.stderr}")

    # ── full compile mode ─────────────────────────────────────────────────────

    def test_compile_mode_creates_graph_and_chains(self):
        """compile = compile-graph + compile-chains; all artifacts must exist."""
        result = self._compile()
        self.assertEqual(result.returncode, 0, f"compile failed:\n{result.stderr}")
        self._assert_compiled_graph()
        self._assert_chains_exist()

    def test_compile_mode_introspection_file_is_non_empty(self):
        """Introspection JSON must be non-empty after compile."""
        self._compile()
        path = os.path.join(self.path, "introspection_result.json")
        self.assertGreater(os.path.getsize(path), 0, "introspection_result.json is empty")

    # ── fuzz mode ─────────────────────────────────────────────────────────────

    def test_fuzz_mode_after_compile_produces_stats(self):
        """fuzz (after compile) produces stats.txt and a fuzzer log."""
        self._compile()
        result = self._fuzz()
        self.assertEqual(result.returncode, 0, f"fuzz failed:\n{result.stderr}")
        self._assert_fuzz_output()

    def test_fuzz_mode_without_compile_exits_with_error(self):
        """fuzz without a prior compile should exit non-zero and print a hint."""
        result = self._fuzz()
        self.assertNotEqual(result.returncode, 0, "fuzz should fail when not compiled")
        combined = result.stdout + result.stderr
        self.assertIn("compile", combined.lower(), "Error message should mention 'compile'")

    # ── run mode (compile + fuzz in one shot) ─────────────────────────────────

    def test_run_mode_compiles_and_fuzzes(self):
        """run = compile + fuzz; all graph, chain, and fuzz artifacts must exist."""
        result = self._run()
        self.assertEqual(result.returncode, 0, f"run mode failed:\n{result.stderr}")
        self._assert_compiled_graph()
        self._assert_chains_exist()
        self._assert_fuzz_output()

    # ── sub-mode pipeline: compile-graph → compile-chains → fuzz ─────────────

    def test_sub_mode_pipeline_graph_chains_fuzz(self):
        """Running compile-graph then compile-chains then fuzz is equivalent to compile + fuzz."""
        r1 = self._compile_graph()
        self.assertEqual(r1.returncode, 0, f"compile-graph failed:\n{r1.stderr}")

        r2 = self._compile_chains()
        self.assertEqual(r2.returncode, 0, f"compile-chains failed:\n{r2.stderr}")

        r3 = self._fuzz()
        self.assertEqual(r3.returncode, 0, f"fuzz failed:\n{r3.stderr}")

        self._assert_compiled_graph()
        self._assert_chains_exist()
        self._assert_fuzz_output()

    # ── --disable-mutations flag ──────────────────────────────────────────────

    def test_disable_mutations_flag_still_produces_chains(self):
        """--disable-mutations should still produce chain files (queries only)."""
        result = self._compile(extra_args=["--disable-mutations"])
        self.assertEqual(result.returncode, 0, f"compile --disable-mutations failed:\n{result.stderr}")
        self._assert_chains_exist()

    def test_disable_mutations_produces_fewer_chains_than_full_compile(self):
        """Chain count with --disable-mutations must be ≤ chain count without it."""

        def _chain_line_count(path: str) -> int:
            chains_dir = os.path.join(path, "compiled", "chains")
            total = 0
            if os.path.isdir(chains_dir):
                for fname in os.listdir(chains_dir):
                    if fname.endswith(".yml"):
                        with open(os.path.join(chains_dir, fname)) as f:
                            total += f.read().count("- node:")
            return total

        # Full compile
        full_path = self.path + "full/"
        os.makedirs(full_path, exist_ok=True)
        _run_cli(full_path, "compile", URL)
        full_count = _chain_line_count(full_path)

        # Mutations-disabled compile (reuse self.path)
        _run_cli(self.path, "compile", URL, ["--disable-mutations"])
        disabled_count = _chain_line_count(self.path)

        shutil.rmtree(full_path)

        self.assertLessEqual(
            disabled_count,
            full_count,
            f"--disable-mutations produced more chains ({disabled_count}) than full compile ({full_count})",
        )

    # ── compile mode is idempotent ────────────────────────────────────────────

    def test_compile_mode_is_idempotent(self):
        """Running compile twice in the same directory should not raise errors."""
        r1 = self._compile()
        r2 = self._compile()
        self.assertEqual(r1.returncode, 0, f"First compile failed:\n{r1.stderr}")
        self.assertEqual(r2.returncode, 0, f"Second compile failed:\n{r2.stderr}")
        self._assert_compiled_graph()
        self._assert_chains_exist()
