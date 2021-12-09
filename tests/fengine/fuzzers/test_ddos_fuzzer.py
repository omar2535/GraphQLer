import unittest
from utils.grammar_parser import GrammarParser


class TestDdosFuzzer(unittest.TestCase):
    def test_fuzzer(self):
        GRAMMAR_FILE_PATH = "./examples/grammar-example.yml"

        grammar_parser = GrammarParser(GRAMMAR_FILE_PATH)
        graph = grammar_parser.generate_dependency_graph()
        datatypes = grammar_parser.get_datatypes()

        print(graph)
        print(datatypes)

        self.assertEqual(1, 1)
