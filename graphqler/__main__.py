"""
Graphler - main start
"""

import sys
import argparse
import importlib.metadata

from graphqler.compiler.compiler import Compiler
from graphqler.fuzzer import Fuzzer
from graphqler.graph import GraphGenerator
from graphqler.utils.stats import Stats
from graphqler.utils.cli_utils import set_auth_token_constant, set_idor_auth_token_constant, is_compiled
from graphqler.utils.config_handler import parse_config, set_config, generate_new_config, does_config_file_exist_in_path
from graphqler.utils.file_utils import get_or_create_directory
from graphqler import config

def run_compile_mode(compiler: Compiler, path: str, url: str):
    """Runs the full compilation pipeline by delegating to compile-graph then compile-chains.

    Args:
        compiler (Compiler): An instance of the Compiler class to use for compilation.  
        path (str): Directory for all compilation outputs to be saved to
        url (str): URL of the target
    """
    print("(C) In compile mode!")
    run_compile_graph_mode(compiler, path, url)
    run_compile_chains_mode(compiler, path, url)
    print("(C) Complete compilation phase")


def run_compile_graph_mode(compiler: Compiler, path: str, url: str):
    """Runs only the introspection / parsing / resolving steps and generates the dependency graph.

    Use this when you want to regenerate the dependency graph without re-running
    chain generation, or when you plan to run ``compile-chains`` separately.

    Args:
        compiler (Compiler): An instance of the Compiler class to use for compilation.
        path (str): Directory for all compilation outputs to be saved to
        url (str): URL of the target
    """
    print("(C) In compile-graph mode!")
    compiler.run()

    print("(C) Finished compiling, starting graph generator")
    graph_generator = GraphGenerator(path)
    graph = graph_generator.get_dependency_graph()
    graph_generator.draw_dependency_graph()

    print("(C) Found", len(graph.nodes), "nodes and", len(graph.edges), "edges")
    print("(C) Complete graph compilation phase (chains not generated)")


def run_compile_chains_mode(compiler: Compiler, path: str, url: str):
    """Generates (or re-generates) fuzzing chains from an already-compiled graph.

    Requires that ``compile`` or ``compile-graph`` has been run first so that the
    compiled YAML files and dependency graph are present on disk.

    Args:
        compiler (Compiler): An instance of the Compiler class to use for chain generation.
        path (str): Directory used during the original compilation.
        url (str): URL of the target
    """

    print("(C) In compile-chains mode!")
    dependency_graph = GraphGenerator(path).get_dependency_graph()
    in_degrees = dict(dependency_graph.in_degree())
    if not in_degrees:
        print("(C) Dependency graph is empty — no chains generated")
        return

    compiler.run_chain_generation_and_save()
    print("(C) Chain generation complete")


def run_fuzz_mode(fuzzer: Fuzzer, path: str, url: str):
    """Runs the program in fuzz mode

    Args:
        fuzzer (Fuzzer): An instance of the Fuzzer class to run
        path (str): Directory for all compilation outputs to be saved to
        url (str): URL of the target
    """
    print("(F) Initializing stats file")
    stats = Stats()
    stats.set_file_paths(path)

    print("(F) Starting fuzzer")
    if not config.USE_OBJECTS_BUCKET:
        print("(F) Ablation mode: objects bucket disabled — no state tracking across requests")
    if not config.USE_DEPENDENCY_GRAPH:
        print("(F) Ablation mode: dependency graph disabled — running all nodes without chain ordering")
    if config.MAX_FUZZING_ITERATIONS != 1:
        print(f"(F) Running up to {config.MAX_FUZZING_ITERATIONS} chain iteration(s)")

    fuzzer.run()

    print("(F) Complete fuzzing phase")


def run_idor_mode(path: str, url: str):
    """Run only the IDOR chain phase (no regular fuzzing).

    Requires a prior --mode compile run with --idor-auth set so that
    IDOR chains were generated into compiled/chains/idor.yml.
    """
    print("(F) Running IDOR-only phase (skipping regular fuzzing)")
    Fuzzer(path, url).run_idor_only()


def run_single_mode(path: str, url: str, name: str):
    print("(F) Running single mode")
    Fuzzer(path, url).run_single(name)


def main(args: dict):
    # Run either compilation or fuzzing mode
    if 'mode' not in args or not args['mode']:
        print("Please provide a mode to run the program in")
        sys.exit(1)

    # compile-chains works from disk — URL not needed; all other modes require it
    if args['mode'] != "compile-chains" and not args.get('url'):
        print(f"--url is required for mode '{args['mode']}'")
        sys.exit(1)

    # If not compile mode, check if compiled directory exists
    if args['mode'] not in ["compile", "compile-graph", "compile-chains", "run", "single", "idor"] and not is_compiled(args['path']):
        print("(!) Compiled directory does not exist, please run in compile mode first")
        sys.exit(1)

    # Set the path if provided and create the directory if it doesn't exist
    if 'path' in args and args['path']:
        config.OUTPUT_DIRECTORY = args['path']
    get_or_create_directory(config.OUTPUT_DIRECTORY)

    # Set proxy if provided
    if 'proxy' in args and args['proxy']:
        config.PROXY = args['proxy']

    # Parse config if provided
    if 'config' in args and args['config']:
        print("(P) Using provided config file")
        new_config = parse_config(args['config'])
        set_config(new_config)
    elif does_config_file_exist_in_path(args['path']):
        print("(P) Using config file in path")
        new_config = parse_config(f"{args['path']}/{config.CONFIG_FILE_NAME}")
        set_config(new_config)
    else:
        print("(P) Generating new config")
        generate_new_config(f"{args['path']}/{config.CONFIG_FILE_NAME}")

    # Parse plugins if defined
    if 'plugins_path' in args and args['plugins_path']:
        config.PLUGINS_PATH = args['plugins_path']
        print(f"(P) Using plugins from {config.PLUGINS_PATH}")

    # CLI overrides — applied after set_config so they always win over the config file
    # Re-assert --path here so that a config file containing OUTPUT_DIRECTORY does not
    # silently override the directory the user explicitly specified on the command line.
    if 'path' in args and args['path']:
        config.OUTPUT_DIRECTORY = args['path']

    if args.get('auth'):
        # Multi-auth support: --auth profile=token or just --auth token (defaults to primary)
        for auth_entry in args['auth']:
            if "=" in auth_entry:
                profile_name, token = auth_entry.split("=", 1)
                config.PROFILES[profile_name] = token
                if profile_name == "primary":
                    set_auth_token_constant(token)
                elif profile_name == "secondary":
                    set_idor_auth_token_constant(token)
            else:
                config.PROFILES["primary"] = auth_entry
                set_auth_token_constant(auth_entry)

    if args.get('idor_auth'):
        set_idor_auth_token_constant(args['idor_auth'])
        config.PROFILES["secondary"] = args['idor_auth']
        print("(P) IDOR secondary auth token set")

    # Apply LLM CLI overrides — these take precedence over config file values
    if args.get('use_llm'):
        config.USE_LLM = True
        print("(P) LLM mode enabled via CLI flag")
    if args.get('llm_report'):
        config.LLM_ENABLE_REPORTER = True
    if args.get('llm_model'):
        config.LLM_MODEL = args['llm_model']
    if args.get('llm_api_key'):
        config.LLM_API_KEY = args['llm_api_key']
    if args.get('llm_base_url'):
        config.LLM_BASE_URL = args['llm_base_url']
    if args.get('llm_max_retries') is not None:
        config.LLM_MAX_RETRIES = args['llm_max_retries']

    # Apply mutation CLI override
    if args.get('disable_mutations'):
        config.DISABLE_MUTATIONS = True
        print("(P) Mutation fuzzing disabled — only Query chains will be generated")

    # Apply ablation CLI overrides
    if args.get('no_objects_bucket'):
        config.USE_OBJECTS_BUCKET = False
        print("(P) Ablation: objects bucket disabled")
    if args.get('no_dependency_graph'):
        config.USE_DEPENDENCY_GRAPH = False
        print("(P) Ablation: dependency graph guidance disabled")
    if args.get('max_iterations') is not None:
        config.MAX_FUZZING_ITERATIONS = args['max_iterations']
        print(f"(P) Max chain iterations set to {config.MAX_FUZZING_ITERATIONS}")
    if args.get('allow_deletion'):
        config.ALLOW_DELETION_OF_OBJECTS = True
        print("(P) Deletion of objects from bucket enabled")
    if args.get('subscriptions'):
        config.SKIP_SUBSCRIPTIONS = False
        print("(P) Subscription fuzzing enabled")

    # Initialize the compiler and fuzzer
    compiler = Compiler(args['path'], args['url'])
    # Start the program
    if args['mode'] == "compile":
        run_compile_mode(compiler, config.OUTPUT_DIRECTORY, args['url'])
    elif args['mode'] == "compile-graph":
        run_compile_graph_mode(compiler, config.OUTPUT_DIRECTORY, args['url'])
    elif args['mode'] == "compile-chains":
        run_compile_chains_mode(compiler, config.OUTPUT_DIRECTORY, args['url'])
    elif args['mode'] == "fuzz":
        fuzzer = Fuzzer(args['path'], args['url'])
        run_fuzz_mode(fuzzer, config.OUTPUT_DIRECTORY, args['url'])
    elif args['mode'] == "run":
        run_compile_mode(compiler, config.OUTPUT_DIRECTORY, args['url'])
        fuzzer = Fuzzer(args['path'], args['url'])
        run_fuzz_mode(fuzzer, config.OUTPUT_DIRECTORY, args['url'])
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

    # Launch MCP server when --mcp is passed (before full argument parsing so
    # that --mode is not required in this path).
    if "--mcp" in sys.argv:
        transport = "stdio"
        if "--mcp-transport" in sys.argv:
            idx = sys.argv.index("--mcp-transport")
            if idx + 1 >= len(sys.argv) or sys.argv[idx + 1].startswith("-"):
                print("Error: --mcp-transport requires a value (e.g. stdio, sse, streamable-http, http).", file=sys.stderr)
                sys.exit(2)
            transport = sys.argv[idx + 1]
        try:
            from graphqler.utils.mcp_utils.server import serve, TRANSPORTS
        except ImportError:
            print(
                "The 'mcp' package is required to run the MCP server.\n"
                "Install it with:  pip install GraphQLer[mcp]",
                file=sys.stderr,
            )
            sys.exit(1)
        if transport not in TRANSPORTS:
            print(f"Invalid transport '{transport}'. Choose from: {', '.join(TRANSPORTS)}", file=sys.stderr)
            sys.exit(1)
        from typing import cast, Literal
        serve(transport=cast(Literal["stdio", "http", "sse", "streamable-http"], transport))
        sys.exit(0)

    # Launch TUI when called with no arguments
    if len(sys.argv) == 1:
        from graphqler.tui.app import GraphQLerApp

        GraphQLerApp().run()
        sys.exit(0)

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="remote host URL (required for all modes except compile-chains)", required=False)
    parser.add_argument("--path", help=f"directory location for files to be saved-to/used-from. Defaults to {config.OUTPUT_DIRECTORY}", required=False)
    parser.add_argument("--config", help="TOML configuration file for the program", required=False)
    parser.add_argument("--mode", help="mode to run the program in", choices=["compile", "compile-graph", "compile-chains", "fuzz", "idor", "run", "single"], required=True)
    parser.add_argument("--auth", help="authentication token(s). Can be 'token' or 'profile=token'. Multiple allowed.", action="append", required=False)
    parser.add_argument("--idor-auth", help="secondary (attacker) auth token for chain-based IDOR testing. Example: 'Bearer secondtoken'", required=False)
    parser.add_argument("--proxy", help="proxy to use for requests (ie. http://127.0.0.1:8080)", required=False)
    parser.add_argument("--node", help="node to run (only used in single mode)", required=False)
    parser.add_argument("--plugins-path", help="path to plugins directory", required=False)
    parser.add_argument("--use-llm", help="enable LLM-powered features: dependency graph inference, endpoint classification, IDOR chain classification, and UAF chain classification (requires LLM_MODEL and credentials)", action="store_true", default=False)
    parser.add_argument("--llm-report", help="generate an LLM vulnerability report (report.md) after fuzzing completes — requires --use-llm", action="store_true", default=False)
    parser.add_argument("--llm-model", help="litellm model string, e.g. 'gpt-4o-mini', 'ollama/llama3', 'anthropic/claude-3-5-haiku-20241022'", required=False)
    parser.add_argument("--llm-api-key", help="API key for the LLM provider (or set OPENAI_API_KEY / ANTHROPIC_API_KEY env var)", required=False)
    parser.add_argument("--llm-base-url", help="custom base URL for LLM endpoint (required for Ollama and LiteLLM proxies)", required=False)
    parser.add_argument("--llm-max-retries", help="number of retries when LLM returns non-JSON (default: 2)", type=int, required=False)
    parser.add_argument("--disable-mutations", help="only generate and run Query chains — all Mutation nodes are excluded from fuzzing", action="store_true", default=False)

    # Ablation / research flags
    parser.add_argument("--no-objects-bucket", help="ablation: disable the objects bucket — requests carry no state from prior responses", action="store_true", default=False)
    parser.add_argument("--no-dependency-graph", help="ablation: disable dependency-graph chain ordering — all nodes run independently without chaining", action="store_true", default=False)
    parser.add_argument("--max-iterations", help=f"number of times to iterate through all chains (default: {config.MAX_FUZZING_ITERATIONS})", type=int, required=False)
    parser.add_argument("--allow-deletion", help="remove objects from the bucket when a DELETE mutation succeeds (default: off)", action="store_true", default=False)
    parser.add_argument("--subscriptions", help="enable fuzzing of GraphQL subscriptions via WebSocket (disabled by default — requires WebSocket support on the target)", action="store_true", default=False)

    parser.add_argument("--version", help="display version", action="store_true")

    # MCP server flags (handled before argument parsing; registered here for --help visibility)
    parser.add_argument("--mcp", help="launch the GraphQLer MCP server (requires pip install GraphQLer[mcp])", action="store_true", default=False)
    parser.add_argument("--mcp-transport", help="MCP transport to use: 'stdio' (default), 'sse', 'streamable-http', or 'http'", default="stdio", choices=["stdio", "sse", "streamable-http", "http"], metavar="TRANSPORT")

    args = parser.parse_args()
    args_as_dict = vars(args)

    # Some massaging
    if args_as_dict['path'] is None:
        args_as_dict['path'] = config.OUTPUT_DIRECTORY
    main(args_as_dict)
