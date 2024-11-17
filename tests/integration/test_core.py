import unittest
from graphqler import core
from graphqler.utils.config_handler import parse_config
from tests.integration.utils.run_api import run_node_project, wait_for_server
import os


class TestCore(unittest.TestCase):
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

        # Wait for the server to to respond
        wait_for_server(cls.URL, timeout=30)

    @classmethod
    def tearDownClass(cls):
        if cls.process and cls.process.pid == cls.process_pid:
            cls.process.kill()
            cls.process.wait()
        os.system(f"rm -rf {cls.PATH}")

    def test_core_functions(self):
        newconfig = parse_config(self.CONFIG_PATH)
        result = core.compile_and_fuzz(self.PATH, self.URL, newconfig)
        objects_bucket: core.ObjectsBucket = result["objects_bucket"]
        api: core.API = result['api']
        stats: core.Stats = result["stats"]
        results = result["results"]

        assert not objects_bucket.is_empty()
        assert api.get_num_objects() > 0
        assert api.get_num_queries() > 0
        assert api.get_num_mutations() > 0
        assert stats.number_of_objects > 0
        assert stats.number_of_successes > 0
        assert stats.number_of_objects > 0
        assert len(results) > 0
