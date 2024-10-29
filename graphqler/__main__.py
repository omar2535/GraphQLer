"""
Graphler - main start
"""

import sys
import argparse
import pprint
import importlib.metadata
import cloudpickle

from graphqler.compiler.compiler import Compiler
from graphqler.fuzzer import Fuzzer, IDORFuzzer
from graphqler.graph import GraphGenerator
from graphqler.utils.stats import Stats
from graphqler.utils.cli_utils import set_auth_token_constant, is_compiled
from graphqler.utils.logging_utils import Logger
from graphqler.utils.config_handler import parse_config, set_constants_with_config
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
    else:
        print("(F) Not using dependency graph")
        objects_bucket = Fuzzer(path, url).run_no_dfs()

    print("(F) Saving objects bucket")
    with open(f"{path}/objects_bucket.pkl", "wb") as f:
        cloudpickle.dump(objects_bucket, f)

    print("(F) Complete fuzzing phase")


def run_idor_mode(path: str, url: str):
    print("(F) Running IDOR fuzzer")
    logger = Logger()
    logger.initialize_loggers("idor", path)
    try:
        with open(f"{path}/objects_bucket.pkl", "rb") as f:
            objects_bucket = cloudpickle.load(f)
            possible_idor_nodes = IDORFuzzer(path, url, objects_bucket).run()
            print("Possible IDOR nodes:")
            pprint.pprint(possible_idor_nodes)
    except FileNotFoundError:
        print("(F) Error: objects_bucket.pkl not found")
        return


def run_single_mode(path: str, url: str, name: str):
    print("(F) Running single mode")
    logger = Logger()
    logger.initialize_loggers("fuzz", path)
    Fuzzer(path, url).run_single(name)


if __name__ == "__main__":
    # If version, display version and exit
    if "--version" in sys.argv:
        version = importlib.metadata.version("GraphQLer")
        print(version)
        sys.exit(0)

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="remote host URL", required=True)
    parser.add_argument("--path", help="directory location for files to be saved-to/used-from", required=True)
    parser.add_argument("--config", help="configuration file for the program", required=False)
    parser.add_argument("--mode", help="mode to run the program in", choices=["compile", "fuzz", "idor", "run", "single"], required=True)
    parser.add_argument("--auth", help="authentication token Example: 'Bearer arandompat-abcdefgh'", required=False)
    parser.add_argument("--proxy", help="proxy to use for requests (ie. http://127.0.0.1:8080)", required=False)
    parser.add_argument("--node", help="node to run (only used in single mode)", required=False)
    parser.add_argument("--version", help="display version", action="store_true")
    args = parser.parse_args()

    # If not compile mode, check if compiled directory exists
    if args.mode not in ["compile", "run"] and not is_compiled(args.path):
        print("(!) Compiled directory does not exist, please run in compile mode first")
        sys.exit(1)

    # Set proxy if provided
    if args.proxy:
        constants.PROXY = args.proxy

    # Set auth token if provided
    if args.auth:
        set_auth_token_constant(args.auth)

    # Parse config if provided
    if args.config:
        config = parse_config(args.config)
        set_constants_with_config(config)

    # Run either compilation or fuzzing mode
    if args.mode == "compile":
        run_compile_mode(args.path, args.url)
    elif args.mode == "fuzz":
        run_fuzz_mode(args.path, args.url)
    elif args.mode == "run":
        run_compile_mode(args.path, args.url)
        run_fuzz_mode(args.path, args.url)
    elif args.mode == "idor":
        run_idor_mode(args.path, args.url)
    elif args.mode == "single":
        if not args.node:
            print("Please provide a node to run in single mode")
            sys.exit(1)
        run_single_mode(args.path, args.url, args.node)
