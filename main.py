"""
Graphler - main start
"""

import sys
import argparse

from compiler.compiler import Compiler
from graph import GraphGenerator


def run_compile_mode(path: str, url: str):
    """Runs the program in compile mode, running two things:
       - Compiler - compiles the objects and resolves dependencies
       - GraphGeneration - links objects together making the graph

    Args:
        path (str): Directory for all compilation outputs to be saved to
        url (str): URL of the target
    """
    print("(+) In compile mode!")
    Compiler(path, url).run()

    print("(+) Finished compiling, starting graph generator")
    GraphGenerator(path).get_dependency_graph()

    print("(+) Complete compilation phase")


def run_fuzz_mode(path: str, url: str):
    """Runs the program in fuzz mode

    Args:
        path (str): Directory for all compilation outputs to be saved to
        url (str): URL of the target
    """
    print("In fuzz mode!")


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--compile", help="turns on the compile mode", action="store_true", required=False)
    parser.add_argument("--fuzz", help="turns on the fuzzing mode", action="store_true", required=False)
    parser.add_argument("--path", help="directory location for saved files and files to be used from", required=True)
    parser.add_argument("--url", help="remote host URL", required=True)
    args = parser.parse_args()

    # Validate arguments
    if not args.compile and not args.fuzz:
        print("(!) Need at least one of --fuzz or --compile modes")
        sys.exit()

    # Run either compilation or fuzzing mode
    if args.compile:
        run_compile_mode(args.path, args.url)
    elif args.fuzz:
        run_fuzz_mode(args.path, args.url)
