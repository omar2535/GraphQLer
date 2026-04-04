"""benchmark_llm_chains.py — compare heuristic vs LLM-annotated dependency chain generation.

Benchmarks specifically the chain-generation component of GraphQLer (compile-chains).
Other LLM-assisted components (e.g. payload generation, response analysis) have their
own benchmark scripts.

For each API the script:
  1. Runs a full compile (introspection + heuristic dependency graph + chains).
  2. Copies the compiled artefacts to an LLM output directory.
  3. Re-runs compile-chains with USE_LLM=True to regenerate chains.yml.
  4. Computes and prints a side-by-side comparison table.
  5. Saves results as JSON to <output_dir>/llm_comparison_results.json.

Usage
-----
    # Basic — default LLM model (gpt-4o-mini, requires OPENAI_API_KEY env var):
    python benchmark/benchmark_llm_chains.py \\
        --output /tmp/llm-chains \\
        --apis http://localhost:4000/graphql:food-delivery \\
               http://localhost:4001/graphql:user-wallet

    # Ollama (local):
    python benchmark/benchmark_llm_chains.py \\
        --output /tmp/llm-chains \\
        --llm-model ollama/gpt-oss:20b \\
        --llm-base-url http://localhost:11434 \\
        --apis http://localhost:4000/graphql:food-delivery \\
               http://localhost:4001/graphql:user-wallet

    # Disable mutations (query chains only):
    python benchmark/benchmark_llm_chains.py \\
        --output /tmp/llm-chains \\
        --disable-mutations \\
        --apis http://localhost:4000/graphql:food-delivery

    # Public API example:
    python benchmark/benchmark_llm_chains.py \\
        --output /tmp/llm-chains \\
        --apis https://rickandmortyapi.com/graphql:rick-and-morty
"""

# flake8: noqa

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import yaml

from graphqler import __main__ as graphqler_main
from graphqler.compiler.compiler import Compiler
from graphqler import config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_chains(path: Path) -> list[list[str]]:
    """Load chains.yml and return a list of node lists."""
    chains_file = path / "compiled" / "chains.yml"
    if not chains_file.exists():
        return []
    data = yaml.safe_load(chains_file.read_text()) or []
    return [entry.get("nodes", []) for entry in data]


def _chain_stats(chains: list[list[str]]) -> dict:
    """Compute summary statistics for a list of chains."""
    if not chains:
        return {"count": 0, "avg_length": 0.0, "max_length": 0, "total_nodes": 0}
    lengths = [len(c) for c in chains]
    return {
        "count": len(chains),
        "avg_length": round(sum(lengths) / len(lengths), 2),
        "max_length": max(lengths),
        "total_nodes": sum(lengths),
    }


def _run_compile(url: str, path: Path):
    """Run heuristic compile (introspection → graph → chains)."""
    config.OUTPUT_DIRECTORY = str(path)
    graphqler_main.run_compile_mode(Compiler(str(path), url), str(path), url)


def _run_llm_chains(url: str, path: Path):
    """Re-run compile-chains only, with USE_LLM=True."""
    config.OUTPUT_DIRECTORY = str(path)
    graphqler_main.run_compile_chains_mode(Compiler(str(path), url), str(path), url)


def _print_table(results: list[dict]):
    """Print a human-readable comparison table to stdout."""
    col_w = [20, 10, 12, 12, 12, 12, 12, 12]
    header = ["API", "Mode", "Chains", "Avg Len", "Max Len", "Total Nodes", "Time (s)", "Status"]

    sep = "  ".join("-" * w for w in col_w)
    row_fmt = "  ".join("{:<" + str(w) + "}" for w in col_w)

    print("\n" + "=" * len(sep))
    print("LLM vs Heuristic Chain Generation Comparison")
    print("=" * len(sep))
    print(row_fmt.format(*header))
    print(sep)

    for r in results:
        for mode in ("heuristic", "llm"):
            s = r[mode]
            status = "OK" if s.get("success") else "ERROR"
            print(row_fmt.format(
                r["api_name"][:col_w[0]],
                mode,
                s.get("count", "-"),
                s.get("avg_length", "-"),
                s.get("max_length", "-"),
                s.get("total_nodes", "-"),
                round(s.get("elapsed_s", 0), 1),
                status,
            ))
        print(sep)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare heuristic vs LLM-annotated dependency chain generation across GraphQL APIs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output", "-o", required=True,
        help="Directory to save all run output and results JSON.",
    )
    parser.add_argument(
        "--apis", nargs="+", required=True, metavar="URL:NAME",
        help="One or more API endpoints in URL:NAME format, e.g. http://localhost:4000/graphql:food-delivery",
    )
    parser.add_argument(
        "--llm-model", default="gpt-4o-mini",
        help="litellm model string (default: gpt-4o-mini). E.g. ollama/llama3, anthropic/claude-3-5-haiku-20241022",
    )
    parser.add_argument(
        "--llm-base-url", default="",
        help="Custom LLM base URL (required for Ollama and LiteLLM proxies).",
    )
    parser.add_argument(
        "--llm-api-key", default="",
        help="LLM API key (or set OPENAI_API_KEY / ANTHROPIC_API_KEY env var).",
    )
    parser.add_argument(
        "--llm-max-retries", type=int, default=2,
        help="Number of retries when LLM returns non-JSON (default: 2).",
    )
    parser.add_argument(
        "--disable-mutations", action="store_true",
        help="Only generate Query chains — skip Mutation nodes.",
    )
    return parser.parse_args()


def run_api(url: str, name: str, output_root: Path, args: argparse.Namespace) -> dict:
    """Run heuristic and LLM compile-chains for one API. Returns a result dict."""
    heuristic_path = output_root / name / "heuristic"
    llm_path = output_root / name / "llm"
    heuristic_path.mkdir(parents=True, exist_ok=True)

    result = {"api_name": name, "url": url, "heuristic": {}, "llm": {}}

    # --- Heuristic compile ---
    print(f"\n[{name}] Running heuristic compile → {heuristic_path}")
    config.DISABLE_MUTATIONS = args.disable_mutations
    config.USE_LLM = False
    t0 = time.time()
    try:
        _run_compile(url, heuristic_path)
        elapsed = round(time.time() - t0, 2)
        chains = _load_chains(heuristic_path)
        result["heuristic"] = {**_chain_stats(chains), "elapsed_s": elapsed, "success": True,
                                "path": str(heuristic_path)}
        print(f"[{name}] Heuristic done: {result['heuristic']['count']} chains in {elapsed}s")
    except Exception as exc:
        result["heuristic"] = {"success": False, "error": str(exc), "elapsed_s": round(time.time() - t0, 2)}
        print(f"[{name}] Heuristic FAILED: {exc}", file=sys.stderr)

    # --- LLM compile-chains ---
    # Copy compiled artefacts (introspection + graph) so LLM only re-generates chains
    print(f"\n[{name}] Running LLM compile-chains → {llm_path}")
    if llm_path.exists():
        shutil.rmtree(llm_path)
    shutil.copytree(heuristic_path, llm_path)

    config.USE_LLM = True
    config.LLM_MODEL = args.llm_model
    config.LLM_BASE_URL = args.llm_base_url
    config.LLM_API_KEY = args.llm_api_key
    config.LLM_MAX_RETRIES = args.llm_max_retries
    config.DISABLE_MUTATIONS = args.disable_mutations

    t0 = time.time()
    try:
        _run_llm_chains(url, llm_path)
        elapsed = round(time.time() - t0, 2)
        chains = _load_chains(llm_path)
        result["llm"] = {**_chain_stats(chains), "elapsed_s": elapsed, "success": True,
                         "path": str(llm_path)}
        print(f"[{name}] LLM done: {result['llm']['count']} chains in {elapsed}s")
    except Exception as exc:
        result["llm"] = {"success": False, "error": str(exc), "elapsed_s": round(time.time() - t0, 2)}
        print(f"[{name}] LLM FAILED: {exc}", file=sys.stderr)

    # Reset LLM flag so subsequent runs start clean
    config.USE_LLM = False
    return result


def main():
    args = parse_args()
    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    # Parse URL:NAME pairs
    apis = []
    for entry in args.apis:
        if ":" not in entry:
            print(f"ERROR: --apis entries must be in URL:NAME format, got: {entry!r}", file=sys.stderr)
            sys.exit(1)
        # Split on last colon to allow URLs with colons (http://...)
        idx = entry.rfind(":")
        url, name = entry[:idx], entry[idx + 1:]
        if not url or not name:
            print(f"ERROR: could not parse URL:NAME from {entry!r}", file=sys.stderr)
            sys.exit(1)
        apis.append((url, name))

    print(f"Running LLM comparison for {len(apis)} API(s)")
    print(f"Output directory: {output_root}")
    print(f"LLM model: {args.llm_model}")
    if args.llm_base_url:
        print(f"LLM base URL: {args.llm_base_url}")
    if args.disable_mutations:
        print("Mutations disabled — query chains only")

    all_results = []
    for url, name in apis:
        r = run_api(url, name, output_root, args)
        all_results.append(r)

    _print_table(all_results)

    # Save JSON results
    results_file = output_root / "llm_chains_results.json"
    results_file.write_text(json.dumps(all_results, indent=2))
    print(f"\nResults saved to {results_file}")


if __name__ == "__main__":
    main()
