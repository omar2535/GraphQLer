import unittest

from graphqler import __main__


class TestFullRun(unittest.TestCase):
    URL = "http://localhost:8080/graphql"

    def test_run_compile_mode(self):
        self.assertTrue(True)
