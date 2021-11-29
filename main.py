"""
Graphler - main start
"""

import sys
from utils.graph_parser import GraphParser
from utils.orchestrator import Orchestrator


def main(grammar_file_path):
    graph = GraphParser().generate_dependency_graph(grammar_file_path)
    orchestrator = Orchestrator(graph)
    orchestrator.orchestrate()


if __name__ == "__main__":
    number_of_arguments = 1

    if len(sys.argv) < number_of_arguments + 1:
        print(f"(+) Requires {number_of_arguments} arguments")
        print(f"(+) Example usage: python3 main.py examples/grammar-example.yml")
        sys.exit()

    file_name = sys.argv[0]
    grammar_file_path = sys.argv[1]

    print("(+) Starting Graphler program")
    main(grammar_file_path)
    print("(+) Ending Graphler program")
