"""
Graphler - main start
"""

import sys
import argparse
import pprint
import importlib.metadata
import cloudpickle as pickle

from graphqler.compiler.compiler import Compiler
from graphqler.fuzzer import Fuzzer, IDORFuzzer
from graphqler.graph import GraphGenerator
from graphqler.utils.stats import Stats
from graphqler.utils.cli_utils import set_auth_token_constant, is_compiled
from graphqler.utils.config_handler import parse_config, set_config
from graphqler import config


def run_compile_mode(path: str, url: str):
    """Runs the program in compile mode, running two things:
       - Compiler - compiles the objects and resolves dependencies
       - GraphGeneration - links objects together making the graph

    Args:
        path (str): Directory for all compilation outputs to be saved to
        url (str): URL of the target
    """
    print("(C) In compile mode!")
    Compiler(path, url).run()

    print("(C) Finished compiling, starting graph generator")
    graph_generator = GraphGenerator(path)
    graph = graph_generator.get_dependency_graph()
    graph_generator.draw_dependency_graph()

    print("(C) Found", len(graph.nodes), "nodes and", len(graph.edges), "edges")
    print("(C) Complete compilation phase")


def run_fuzz_mode(path: str, url: str):
    """Runs the program in fuzz mode

    Args:
        path (str): Directory for all compilation outputs to be saved to
        url (str): URL of the target
    """
    print("(F) Initializing stats file")
    stats = Stats()
    stats.set_file_paths(path)

    print("(F) Starting fuzzer")
    if not config.USE_OBJECTS_BUCKET:
        print("(F) Not using Objects Bucket")

    if config.USE_DEPENDENCY_GRAPH:
        print("(F) Running in dependency graph mode")
        Fuzzer(path, url).run()
    else:
        print("(F) Not using dependency graph")
        Fuzzer(path, url).run_no_dfs()

    print("(F) Complete fuzzing phase")


def run_idor_mode(path: str, url: str):
    print("(F) Running IDOR fuzzer")
    try:
        with open(f"{path}/{config.OBJECTS_BUCKET_PICKLE_FILE_NAME}", "rb") as f:
            objects_bucket = pickle.load(f)
            possible_idor_nodes = IDORFuzzer(path, url, objects_bucket).run()
            print("Possible IDOR nodes:")
            pprint.pprint(possible_idor_nodes)
    except FileNotFoundError:
        print("(F) Error: objects_bucket.pkl not found")
        return


def run_single_mode(path: str, url: str, name: str):
    print("(F) Running single mode")
    Fuzzer(path, url).run_single(name)


def main(args: dict):
    # Run either compilation or fuzzing mode
    if 'mode' not in args or not args['mode']:
        print("Please provide a mode to run the program in")
        sys.exit(1)

    # If not compile mode, check if compiled directory exists
    if args['mode'] not in ["compile", "run", "single", "idor"] and (not is_compiled(args['path']) or not is_compiled(config.OUTPUT_DIRECTORY)):
        print("(!) Compiled directory does not exist, please run in compile mode first")
        sys.exit(1)

    # Set the path if provided
    if 'path' in args and args['path']:
        config.OUTPUT_DIRECTORY = args['path']

    # Set proxy if provided
    if 'proxy' in args and args['proxy']:
        config.PROXY = args['proxy']

    # Set auth token if provided
    if 'auth' in args and args['auth']:
        set_auth_token_constant(args['auth'])

    # Parse config if provided
    if args['config'] and args['config']:
        new_config = parse_config(args['config'])
        set_config(new_config)

    # Parse plugins if defined
    if 'plugins_path' in args and args['plugins_path']:
        config.PLUGINS_PATH = args['plugins_path']
        print(f"(P) Using plugins from {config.PLUGINS_PATH}")

    if args['mode'] == "compile":
        run_compile_mode(config.OUTPUT_DIRECTORY, args['url'])
    elif args['mode'] == "fuzz":
        run_fuzz_mode(config.OUTPUT_DIRECTORY, args['url'])
    elif args['mode'] == "run":
        run_compile_mode(config.OUTPUT_DIRECTORY, args['url'])
        run_fuzz_mode(config.OUTPUT_DIRECTORY, args['url'])
    elif args['mode'] == "idor":
        run_idor_mode(config.OUTPUT_DIRECTORY, args['url'])
    elif args['mode'] == "single":
        if 'node' not in args or not args['node']:
            print("Please provide a node to run in single mode")
            sys.exit(1)
        run_single_mode(args['path'], args['url'], args['node'])


# If running as a CLI
if __name__ == "__main__":
    # If version, display version and exit
    if "--version" in sys.argv:
        version = importlib.metadata.version("GraphQLer")
        print(version)
        sys.exit(0)

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="remote host URL", required=True)
    parser.add_argument("--path", help=f"directory location for files to be saved-to/used-from. Defaults to {config.OUTPUT_DIRECTORY}", required=False)
    parser.add_argument("--config", help="configuration file for the program", required=False)
    parser.add_argument("--mode", help="mode to run the program in", choices=["compile", "fuzz", "idor", "run", "single"], required=True)
    parser.add_argument("--auth", help="authentication token Example: 'Bearer arandompat-abcdefgh'", required=False)
    parser.add_argument("--proxy", help="proxy to use for requests (ie. http://127.0.0.1:8080)", required=False)
    parser.add_argument("--node", help="node to run (only used in single mode)", required=False)
    parser.add_argument("--plugins-path", help="path to plugins directory", required=False)
    parser.add_argument("--version", help="display version", action="store_true")

    args = parser.parse_args()
    args_as_dict = vars(args)

    # Some massaging
    if args_as_dict['path'] is None:
        args_as_dict['path'] = config.OUTPUT_DIRECTORY
    main(args_as_dict)
