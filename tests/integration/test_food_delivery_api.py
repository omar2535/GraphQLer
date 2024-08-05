import unittest

from graphqler import __main__
from graphqler import constants
from tests.integration.utils.stats import get_percent_query_mutation_success

import os


class TestFoodDeliveryAPI(unittest.TestCase):
    URL = "http://localhost:4000/graphql"
    PATH = "ci-test/"

    @classmethod
    def setUpClass(self):
        __main__.run_compile_mode(self.PATH, self.URL)

    def test_run_compile_mode_generates_valid_introspection_file(self):
        __main__.run_compile_mode(self.PATH, self.URL)
        introspection_path = os.path.join(self.PATH, constants.INTROSPECTION_RESULT_FILE_NAME)
        self.assertTrue(os.path.exists(introspection_path))
        self.assertGreater(os.path.getsize(introspection_path), 0)

    def test_run_fuzz_mode_generates_valid_stats_file(self):
        __main__.run_fuzz_mode(self.PATH, self.URL)
        stats_path = os.path.join(self.PATH, constants.STATS_FILE_PATH)
        self.assertTrue(os.path.exists(stats_path))
        self.assertGreater(os.path.getsize(stats_path), 0)

    def test_run_single_mode_generates_valid_stats_file(self):
        __main__.run_single_mode(self.PATH, self.URL, "Query")
        stats_path = os.path.join(self.PATH, constants.STATS_FILE_PATH)
        self.assertTrue(os.path.exists(stats_path))
        self.assertGreater(os.path.getsize(stats_path), 0)

    def test_run_fuzz_mode_has_success_over_seventy_percent(self):
        __main__.run_fuzz_mode(self.PATH, self.URL)
        stats_path = os.path.join(self.PATH, constants.STATS_FILE_PATH)
        percentage = get_percent_query_mutation_success(stats_path)
        print(percentage)
        self.assertTrue(percentage >= 70)
