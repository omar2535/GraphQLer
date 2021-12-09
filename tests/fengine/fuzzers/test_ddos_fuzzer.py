import unittest
from fengine.fuzzers.ddos_fuzzer import DDOSFuzzer
from graphqler_types.graphql_request import GraphqlRequest
from utils.grammar_parser import GrammarParser


class TestDdosFuzzer(unittest.TestCase):
    def test_fuzzer(self):
        test_request = GraphqlRequest(
            graphqlQueryType="mutation",
            name="createTodo",
            body=None,
            params=[{"name": "title", "type": "String"}, {"name": "completed", "type": "Boolean"}],
        )

        ddos_fuzzer = DDOSFuzzer(test_request)
        ddos_fuzzer.create_fuzzed_queries()
        breakpoint()

        self.assertEqual(1, 1)
