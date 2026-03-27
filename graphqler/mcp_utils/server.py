"""MCP server for GraphQLer.

Exposes GraphQLer's compile, fuzz, and run operations as MCP tools so that AI
assistants (Claude Desktop, Cursor, etc.) can drive GraphQL API security testing
directly via the Model Context Protocol.

Transport: stdio by default (start with ``python -m graphqler --mcp``).
"""

from __future__ import annotations

import io
import json
import traceback
from contextlib import redirect_stdout
from pathlib import Path
from typing import Annotated

# try:
from fastmcp import FastMCP
# except ImportError as exc:  # pragma: no cover
#     raise ImportError(
#         "The 'mcp' package is required to run the GraphQLer MCP server. "
#         "Install it with:  pip install GraphQLer[mcp]"
#     ) from exc

from graphqler import config
from graphqler.utils.cli_utils import is_compiled

# ---------------------------------------------------------------------------
# Server definition
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="GraphQLer",
    instructions=(
        "GraphQLer is a context-aware GraphQL API security fuzzing tool. "
        "Use these tools to compile (introspect) and fuzz GraphQL APIs for security vulnerabilities. "
        "Typical workflow:\n"
        "1. compile(url, path) — introspect the API, build the dependency graph, and generate fuzzing chains.\n"
        "2. fuzz(url, path)    — run the fuzzer against the compiled artifacts.\n"
        "   Or combine both steps with: run(url, path)\n\n"
        "After fuzzing you can inspect the schema and results via the resources exposed by this server."
    ),
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _reset_singletons() -> None:
    """Clear cached singleton instances so each tool call starts with a clean state."""
    from graphqler.utils.stats import Stats
    from graphqler.utils.objects_bucket import ObjectsBucket

    Stats.reset()
    ObjectsBucket.reset()


def _apply_auth(auth: str | None) -> None:
    """Apply an auth token to the global config."""
    if auth:
        from graphqler.utils.cli_utils import set_auth_token_constant

        set_auth_token_constant(auth)


def _capture(fn, *args, **kwargs):
    """Run *fn* and return (stdout_text, return_value, error_text)."""
    buf = io.StringIO()
    error_text = ""
    result = None
    try:
        with redirect_stdout(buf):
            result = fn(*args, **kwargs)
    except Exception:
        error_text = traceback.format_exc()
    return buf.getvalue(), result, error_text


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def compile(
    url: Annotated[str, "GraphQL API endpoint URL (e.g. http://localhost:4000/graphql)"],
    path: Annotated[str, "Output directory for compilation artifacts"] = "graphqler-output",
    auth: Annotated[str | None, "Authorization header value (e.g. 'Bearer mytoken')"] = None,
) -> str:
    """Compile a GraphQL API: run introspection, parse the schema, build the dependency graph, and generate fuzzing chains.

    Must be run before fuzz(). Returns a summary of what was compiled.
    """
    from graphqler.compiler.compiler import Compiler
    from graphqler.graph import GraphGenerator
    from graphqler.__main__ import run_compile_mode

    _reset_singletons()
    config.OUTPUT_DIRECTORY = path
    _apply_auth(auth)

    from graphqler.utils.file_utils import get_or_create_directory

    get_or_create_directory(path)

    compiler = Compiler(path, url)
    stdout, _, error = _capture(run_compile_mode, compiler, path, url)

    if error:
        return f"Compilation failed:\n{error}\n\nOutput:\n{stdout}"

    # Build a brief summary from the dependency graph
    try:
        graph = GraphGenerator(path).get_dependency_graph()
        node_count = len(graph.nodes)
        edge_count = len(graph.edges)
        summary = f"Compilation complete.\nNodes: {node_count}  Edges: {edge_count}\n"
    except Exception:
        summary = "Compilation complete.\n"

    return summary + (f"\nOutput:\n{stdout}" if stdout else "")


@mcp.tool()
def fuzz(
    url: Annotated[str, "GraphQL API endpoint URL (must match the URL used during compile)"],
    path: Annotated[str, "Output directory that contains the compiled artifacts"] = "graphqler-output",
    auth: Annotated[str | None, "Authorization header value (e.g. 'Bearer mytoken')"] = None,
) -> str:
    """Fuzz a previously compiled GraphQL API for security vulnerabilities.

    Requires compile() to have been run first for the same *path*.
    Returns a summary of vulnerabilities found and fuzzing statistics.
    """
    from graphqler.fuzzer import Fuzzer
    from graphqler.utils.stats import Stats
    from graphqler.__main__ import run_fuzz_mode

    if not is_compiled(path):
        return (
            f"The path '{path}' does not contain compiled artifacts. "
            "Please run compile() first."
        )

    _reset_singletons()
    config.OUTPUT_DIRECTORY = path
    _apply_auth(auth)

    stats = Stats()
    stats.set_file_paths(path)

    fuzzer = Fuzzer(path, url)
    stdout, _, error = _capture(run_fuzz_mode, fuzzer, path, url)

    if error:
        return f"Fuzzing failed:\n{error}\n\nOutput:\n{stdout}"

    # Build summary from stats — fuzzer.run() uses multiprocessing so stats are written to
    # disk by the child process; load them back into the parent-process singleton here.
    stats_obj = Stats().load()
    lines = [
        "Fuzzing complete.",
        f"Successes: {stats_obj.number_of_successes}",
        f"Failures:  {stats_obj.number_of_failures}",
    ]

    vulns = stats_obj.get_formatted_vulnerabilites()
    if vulns.strip():
        lines.append("\nVulnerabilities found:")
        lines.append(vulns)
    else:
        lines.append("No vulnerabilities detected.")

    return "\n".join(lines) + (f"\n\nOutput:\n{stdout}" if stdout else "")


@mcp.tool()
def run(
    url: Annotated[str, "GraphQL API endpoint URL (e.g. http://localhost:4000/graphql)"],
    path: Annotated[str, "Output directory for all artifacts"] = "graphqler-output",
    auth: Annotated[str | None, "Authorization header value (e.g. 'Bearer mytoken')"] = None,
) -> str:
    """Run the full GraphQLer pipeline: compile then fuzz in a single step.

    Equivalent to calling compile() followed by fuzz() with the same arguments.
    Returns a combined summary of compilation and fuzzing results.
    """
    compile_result = compile(url=url, path=path, auth=auth)
    if compile_result.startswith("Compilation failed:"):
        return compile_result

    fuzz_result = fuzz(url=url, path=path, auth=auth)
    return f"=== Compile ===\n{compile_result}\n=== Fuzz ===\n{fuzz_result}"


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource(
    "graphqler://schema/{path}",
    name="GraphQL Schema Info",
    description="Compiled schema information (queries, mutations, objects, etc.) for the given output directory.",
    mime_type="application/json",
)
def get_schema_info(path: str) -> str:
    """Return compiled schema information as JSON for the given output directory."""
    if not is_compiled(path):
        return json.dumps({"error": f"Path '{path}' has not been compiled yet. Run compile() first."})

    from graphqler.utils.api import API

    try:
        api = API(save_path=path)
        data = {
            "queries": list(api.queries.keys()),
            "mutations": list(api.mutations.keys()),
            "objects": list(api.objects.keys()),
            "input_objects": list(api.input_objects.keys()),
            "enums": list(api.enums.keys()),
            "unions": list(api.unions.keys()),
            "interfaces": list(api.interfaces.keys()),
            "counts": {
                "queries": api.get_num_queries(),
                "mutations": api.get_num_mutations(),
                "objects": api.get_num_objects(),
                "input_objects": api.get_num_input_objects(),
                "enums": api.get_num_enums(),
                "unions": api.get_num_unions(),
                "interfaces": api.get_num_interfaces(),
            },
        }
        return json.dumps(data, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.resource(
    "graphqler://results/{path}",
    name="Fuzzing Results",
    description="Fuzzing results and vulnerability findings for the given output directory.",
    mime_type="application/json",
)
def get_fuzzing_results(path: str) -> str:
    """Return fuzzing results and vulnerability findings as JSON for the given output directory."""
    stats_file = Path(path) / config.STATS_FILE_NAME
    json_file = Path(path) / config.STATS_FILE_NAME.replace(".txt", ".json")

    # Prefer machine-readable JSON stats if available
    if json_file.exists():
        try:
            return json_file.read_text(encoding="utf-8")
        except Exception:
            pass

    if stats_file.exists():
        try:
            return json.dumps({"stats_text": stats_file.read_text(encoding="utf-8")})
        except Exception:
            pass

    return json.dumps({"error": f"No fuzzing results found in '{path}'. Run fuzz() first."})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def serve(transport: str = "stdio") -> None:
    """Start the GraphQLer MCP server.

    Args:
        transport: MCP transport to use.  Supported values: ``"stdio"`` (default),
            ``"sse"``, ``"streamable-http"``.
    """
    mcp.run(transport=transport)
