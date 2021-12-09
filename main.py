"""
Graphler - main start
"""

import sys
from utils.grammar_parser import GrammarParser
from utils.orchestrator import Orchestrator


def main(grammar_file_path, end_point_path):
    grammar_parser = GrammarParser(grammar_file_path)
    graph = grammar_parser.generate_dependency_graph()
    datatypes = grammar_parser.get_datatypes()

    # TODO: remove me!
    print(datatypes)

    orchestrator = Orchestrator(graph, end_point_path)
    orchestrator.orchestrate()


if __name__ == "__main__":
    number_of_arguments = 2

    if len(sys.argv) < number_of_arguments + 1:
        print(f"(+) Requires {number_of_arguments} arguments")
        print(f"(+) Example usage: python3 main.py examples/grammar-example.yml http://localhost:1234")
        sys.exit()

    file_name = sys.argv[0]
    grammar_file_path = sys.argv[1]
    end_point_path = sys.argv[2]

    print("(+) Starting Graphler program")
    main(grammar_file_path)
    print("(+) Ending Graphler program")
