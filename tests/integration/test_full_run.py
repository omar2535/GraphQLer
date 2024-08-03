import unittest

from graphqler import __main__


class TestFullRun(unittest.TestCase):
    URL = "http://localhost:8080/graphql"

    def test_run_compile_mode(self):
        self.assertIsNone(__main__.run_compile_mode('path', 'url'))

    def test_run_fuzz_mode(self):
        self.assertIsNone(__main__.run_fuzz_mode('path', 'url'))
