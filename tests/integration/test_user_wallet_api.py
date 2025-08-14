import unittest
from graphqler import __main__
from graphqler import config
from tests.integration.utils.stats import get_percent_query_mutation_success
from tests.integration.utils.run_api import run_node_project, wait_for_server
import os
import shutil



class TestUserWalletApi(unittest.TestCase):
    PORT = 4001
    URL = f"http://localhost:{PORT}/graphql"
    PATH = "ci-test-user-wallet-api/"
    API_PATH = "tests/test-apis/user-wallet-api"
    CONFIG_PATH = "tests/test-apis/test_configs/user_wallet_api_config.toml"
    process = None
    process_pid = None

    @classmethod
    def setUpClass(cls):
        # Start the GrapQL server
        cls.process = run_node_project(cls.API_PATH, [], str(cls.PORT))
        cls.process_pid = cls.process.pid

        # Parse the config
        config = __main__.parse_config(cls.CONFIG_PATH)
        __main__.set_config(config)

        # Wait for the server to to respond
        wait_for_server(cls.URL, timeout=30)

    @classmethod
    def tearDownClass(cls):
        if cls.process and cls.process.pid == cls.process_pid:
            cls.process.kill()
            cls.process.wait()
        if os.path.exists(cls.PATH):
            try:
                shutil.rmtree(cls.PATH)
            except Exception as e:
                pass

    def test_run_compile_mode_generates_valid_introspection_file(self):
        print(self.PATH, self.URL)
        __main__.run_compile_mode(self.PATH, self.URL)
        introspection_path = os.path.join(self.PATH, config.INTROSPECTION_RESULT_FILE_NAME)
        self.assertTrue(os.path.exists(introspection_path))
        self.assertGreater(os.path.getsize(introspection_path), 0)

    def test_run_fuzz_mode_generates_valid_stats_file(self):
        print(self.PATH, self.URL)
        __main__.run_compile_mode(self.PATH, self.URL)
        __main__.run_fuzz_mode(self.PATH, self.URL)
        stats_path = os.path.join(self.PATH, config.STATS_FILE_NAME)
        self.assertTrue(os.path.exists(stats_path))
        self.assertGreater(os.path.getsize(stats_path), 0)

    def test_run_single_mode_generates_valid_stats_file(self):
        print(self.PATH, self.URL)
        __main__.run_compile_mode(self.PATH, self.URL)
        __main__.run_single_mode(self.PATH, self.URL, "getCurrentRate")
        stats_path = os.path.join(self.PATH, config.STATS_FILE_NAME)
        self.assertTrue(os.path.exists(stats_path))
        self.assertGreater(os.path.getsize(stats_path), 0)

    def test_run_fuzz_mode_has_success_over_ninety_percent(self):
        print(self.PATH, self.URL)
        __main__.run_compile_mode(self.PATH, self.URL)
        __main__.run_fuzz_mode(self.PATH, self.URL)
        stats_path = os.path.join(self.PATH, config.STATS_FILE_NAME)
        percentage = get_percent_query_mutation_success(stats_path)
        self.assertTrue(percentage >= 80)
