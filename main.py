"""
Graphler - main start
"""

from utils.graph_parser import GraphParser
from utils.orchestrator import Orchestrator


def main():
    print("(+) Starting Graphler program")


    graph = GraphParser()
    orchestrator = Orchestrator(graph)
    orchestrator.orchestrate()

    print("(+) Endine graphler program")



if __name__ == "__main__":
    main()