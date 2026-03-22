from graphqler import __main__
from graphqler import config
from tests.e2e.utils.stats import get_percent_query_mutation_success
from tests.e2e.utils.run_api import run_node_project, wait_for_server
from tests.e2e.utils.base import GraphQLerIntegrationTestCase
import os
import shutil

class TestFoodDeliveryAPI(GraphQLerIntegrationTestCase):
    PORT = 4000
    URL = f"http://localhost:{PORT}/graphql"
    PATH = "ci-test-food-delivery-api/"
    API_PATH = "sample-graphql-apis/food-delivery-api"
    CONFIG_PATH = "sample-graphql-apis/test_configs/food_delivery_api_config.toml"
    process = None
    process_pid = None

    @classmethod
    def setUpClass(cls):
        # Start the GrapQL server
        node_cmd = shutil.which("node")
        cls.process = run_node_project(cls.API_PATH, [f"{node_cmd} dbinitializer.js"], str(cls.PORT))
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
            shutil.rmtree(cls.PATH)

    def test_run_compile_mode_generates_valid_introspection_file(self):
        self._compile()
        introspection_path = os.path.join(self.PATH, config.INTROSPECTION_RESULT_FILE_NAME)
        self.assertTrue(os.path.exists(introspection_path))
        self.assertGreater(os.path.getsize(introspection_path), 0)

    def test_run_fuzz_mode_generates_valid_stats_file(self):
        self._compile()
        self._fuzz()
        stats_path = os.path.join(self.PATH, config.STATS_FILE_NAME)
        self.assertTrue(os.path.exists(stats_path))
        self.assertGreater(os.path.getsize(stats_path), 0)

    def test_run_single_mode_generates_valid_stats_file(self):
        self._compile()
        self._single("Query")
        stats_path = os.path.join(self.PATH, config.STATS_FILE_NAME)
        self.assertTrue(os.path.exists(stats_path))
        self.assertGreater(os.path.getsize(stats_path), 0)

    def test_run_fuzz_mode_has_success_over_seventy_percent(self):
        self._compile()
        self._fuzz()
        stats_path = os.path.join(self.PATH, config.STATS_FILE_NAME)
        percentage = get_percent_query_mutation_success(stats_path)
        self.assertTrue(percentage >= 70)
