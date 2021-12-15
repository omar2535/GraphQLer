"""
Graphler - main start
"""

import sys
from utils.grammar_parser import GrammarParser
from utils.orchestrator import Orchestrator


def main(grammar_file_path, end_point_path, max_length=2):
    grammar_parser = GrammarParser(grammar_file_path)
    graph = grammar_parser.generate_dependency_graph()
    datatypes = grammar_parser.get_datatypes()

    # TODO: remove me!
    print(datatypes)

    orchestrator = Orchestrator(graph, int(max_length), [], end_point_path, datatypes)
    orchestrator.orchestrate()


if __name__ == "__main__":
    number_of_arguments = 3

    if len(sys.argv) < number_of_arguments + 1:
        print(f"(+) Requires {number_of_arguments} arguments")
        print(f"(+) Example usage: python3 main.py examples/grammar-example.yml http://localhost:3000 3")
        sys.exit()

    file_name = sys.argv[0]
    grammar_file_path = sys.argv[1]
    end_point_path = sys.argv[2]
    max_length = sys.argv[3]

    print("(+) Starting Graphler program")
    main(grammar_file_path, end_point_path, max_length)
    print("(+) Ending Graphler program")
