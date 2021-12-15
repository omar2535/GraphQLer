from requests import status_codes
from utils.orchestrator2 import Orchestrator2
from utils.grammar_parser import GrammarParser


def test_orchestrator2():
    grammar_file_path = "examples/grammar-example.yml"
    grammar_parser = GrammarParser(grammar_file_path)
    graph = grammar_parser.generate_dependency_graph()
    datatypes = grammar_parser.get_datatypes()

    Orchestrator2(graph, 2, [], "http://localhost:3000", datatypes)
    # TODO: Finish this test


def fake_render():
    return [[], []]
