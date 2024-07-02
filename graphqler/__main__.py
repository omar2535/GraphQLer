"""
Graphler - main start
"""

import sys
import pickle
import argparse
import pprint

from graphqler.compiler import Compiler
from graphqler.fuzzer import Fuzzer, IDORFuzzer
from graphqler.graph import GraphGenerator
from graphqler.utils.stats import Stats
from graphqler.utils.argument_parser import set_auth_token_constant
from graphqler.utils.logging_utils import Logger
from graphqler import constants


def run_compile_mode(path: str, url: str):
    """Runs the program in compile mode, running two things:
       - Compiler - compiles the objects and resolves dependencies
       - GraphGeneration - links objects together making the graph

    Args:
        path (str): Directory for all compilation outputs to be saved to
        url (str): URL of the target
    """
    print("(F) Initializing log files")
    logger = Logger()
    logger.initialize_loggers("compile", path)

    print("(C) In compile mode!")
    Compiler(path, url).run()

    print("(C) Finished compiling, starting graph generator")
    graph_generator = GraphGenerator(path)
    graph_generator.get_dependency_graph()
    graph_generator.draw_dependency_graph()

    print("(C) Complete compilation phase")


def run_fuzz_mode(path: str, url: str):
    """Runs the program in fuzz mode

    Args:
        path (str): Directory for all compilation outputs to be saved to
        url (str): URL of the target
    """
    print("(F) Initializing log files")
    logger = Logger()
    logger.initialize_loggers("fuzz", path)

    print("(F) Initializing stats file")
    stats = Stats()
    stats.set_file_path(path)

    print("(F) Starting fuzzer")
    if not constants.USE_OBJECTS_BUCKET:
        print("(F) Not using Objects Bucket")

    if constants.USE_DEPENDENCY_GRAPH:
        print("(F) Running in dependency graph mode")
        objects_bucket = Fuzzer(path, url).run()
        pprint.pprint(objects_bucket)
    else:
        print("(F) Not using dependency graph")
        objects_bucket = Fuzzer(path, url).run_no_dfs()
        pprint.pprint(objects_bucket)

    print("(F) Saving objects bucket")
    with open(f"{path}/objects_bucket.pkl", "wb") as f:
        pickle.dump(objects_bucket, f)

    print("(F) Complete fuzzing phase")


def run_idor_mode(path: str, url: str):
    print("(F) Running IDOR fuzzer")
    logger = Logger()
    logger.initialize_loggers("idor", path)
    try:
        with open(f"{path}/objects_bucket.pkl", "rb") as f:
            objects_bucket = pickle.load(f)
            possible_idor_nodes = IDORFuzzer(path, url, objects_bucket).run()
            print("Possible IDOR nodes:")
            pprint.pprint(possible_idor_nodes)
    except FileNotFoundError:
        print("(F) Error: objects_bucket.pkl not found")
        return


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--compile", help="runs on compile mode", action="store_true", required=False)
    parser.add_argument("--fuzz", help="runs on fuzzing mode", action="store_true", required=False)
    parser.add_argument("--idor", help="run on IDOR checking mode", action="store_true", required=False)
    parser.add_argument("--run", help="run both the compiler and fuzzer (equivalent of running --compile then running --fuzz)", action="store_true", required=False)
    parser.add_argument("--path", help="directory location for saved files and files to be used from", required=True)
    parser.add_argument("--auth", help="authentication token Example: 'Bearer arandompat-abcdefgh'", required=False)
    parser.add_argument("--url", help="remote host URL", required=True)
    args = parser.parse_args()

    # Validate arguments
    if not args.compile and not args.fuzz and not args.run and not args.idor:
        print("(!) Need at one of [--fuzz. --compile, --run, --idor] to run the program")
        sys.exit()

    # Set auth token
    if args.auth:
        set_auth_token_constant(args.auth)

    # Run either compilation or fuzzing mode
    if args.compile:
        run_compile_mode(args.path, args.url)
    elif args.fuzz:
        run_fuzz_mode(args.path, args.url)
    elif args.run:
        run_compile_mode(args.path, args.url)
        run_fuzz_mode(args.path, args.url)
    elif args.idor:
        run_idor_mode(args.path, args.url)
