# flake8: noqa
"""Ablation study for GraphQLer.

Runs four configurations of GraphQLer on each API to isolate the contribution of
(a) the dependency graph and (b) the objects bucket to operation coverage.

Configurations per API:
  1. baseline   — USE_DEPENDENCY_GRAPH=False, USE_OBJECTS_BUCKET=False
  2. graph_only — USE_DEPENDENCY_GRAPH=True,  USE_OBJECTS_BUCKET=False
  3. bucket_only— USE_DEPENDENCY_GRAPH=False, USE_OBJECTS_BUCKET=True
  4. full       — USE_DEPENDENCY_GRAPH=True,  USE_OBJECTS_BUCKET=True  (full GraphQLer)

Results are written to ablation_results.csv alongside this script.
"""

import csv
import json
import multiprocessing
import time
from os import path

from graphqler.__main__ import run_compile_mode, run_fuzz_mode
from graphqler.compiler.compiler import Compiler
from graphqler.fuzzer import Fuzzer
from graphqler import config

# ------------------------------------------------------------------
# APIs to evaluate
# ------------------------------------------------------------------
APIS = [
    ("https://countries.trevorblades.com/", "ablation/countries/"),
    ("https://rickandmortyapi.com/graphql", "ablation/rick-and-morty/"),
    ("https://graphqlzero.almansi.me/api", "ablation/graphql-zero/"),
    ("https://graphql.anilist.co/", "ablation/anilist/"),
    ("https://portal.ehri-project.eu/api/graphql", "ablation/ehri/"),
    ("https://www.universe.com/graphql", "ablation/universe/"),
    ("https://beta.pokeapi.co/graphql/v1beta", "ablation/pokeapi/"),
    ("https://hivdb.stanford.edu/graphql", "ablation/hivdb/"),
    ("https://api.tcgdex.net/v2/graphql", "ablation/tcgdex/"),
]

# Time budget in seconds (same for all configurations to ensure fair comparison)
TIME_BUDGET = 60

# Fixed settings shared across all configurations
SHARED_CONFIG = {
    "SKIP_DOS_ATTACKS": True,
    "SKIP_MISC_ATTACKS": True,
    "SKIP_INJECTION_ATTACKS": True,
    "SKIP_MAXIMAL_PAYLOADS": True,
    "DEBUG": False,
    "MAX_TIME": TIME_BUDGET,
}

# The four ablation configurations
CONFIGURATIONS = [
    {"name": "baseline",     "USE_DEPENDENCY_GRAPH": False, "USE_OBJECTS_BUCKET": False},
    {"name": "graph_only",   "USE_DEPENDENCY_GRAPH": True,  "USE_OBJECTS_BUCKET": False},
    {"name": "bucket_only",  "USE_DEPENDENCY_GRAPH": False, "USE_OBJECTS_BUCKET": True},
    {"name": "full",         "USE_DEPENDENCY_GRAPH": True,  "USE_OBJECTS_BUCKET": True},
]

OUTPUT_CSV = path.join(path.dirname(__file__), "ablation_results.csv")


def _apply_config(cfg: dict):
    """Apply a configuration dictionary to the global config module."""
    for k, v in cfg.items():
        setattr(config, k, v)


def _read_stats_json(output_path: str) -> dict:
    """Read the machine-readable stats JSON produced by GraphQLer after a fuzz run."""
    stats_json_name = config.STATS_FILE_NAME.replace(".txt", ".json") if config.STATS_FILE_NAME.endswith(".txt") else config.STATS_FILE_NAME + ".json"
    stats_path = path.join(output_path, stats_json_name)
    if path.exists(stats_path):
        with open(stats_path) as f:
            return json.load(f)
    return {}


def run_single(api_url: str, base_path: str, cfg: dict) -> dict:
    """Compile and fuzz a single API with a given configuration.

    Returns a dict with coverage metrics.
    """
    cfg_name = cfg["name"]
    output_path = f"{base_path}{cfg_name}/"

    _apply_config(SHARED_CONFIG)
    _apply_config({k: v for k, v in cfg.items() if k != "name"})

    start = time.time()
    try:
        run_compile_mode(Compiler(output_path, api_url), output_path, api_url)
        run_fuzz_mode(Fuzzer(output_path, api_url), output_path, api_url)
        elapsed = time.time() - start
        stats = _read_stats_json(output_path)
        coverage = stats.get("operation_coverage", {})
        return {
            "api": api_url,
            "config": cfg_name,
            "covered": coverage.get("covered", 0),
            "total": coverage.get("total", 0),
            "coverage_rate": coverage.get("rate", 0.0),
            "elapsed_seconds": round(elapsed, 1),
            "error": "",
        }
    except Exception as exc:
        return {
            "api": api_url,
            "config": cfg_name,
            "covered": 0,
            "total": 0,
            "coverage_rate": 0.0,
            "elapsed_seconds": round(time.time() - start, 1),
            "error": str(exc),
        }


def run_api(api_url: str, base_path: str) -> list[dict]:
    """Run all four ablation configurations for a single API sequentially."""
    results = []
    for cfg in CONFIGURATIONS:
        print(f"[ablation] {api_url}  config={cfg['name']}")
        result = run_single(api_url, base_path, cfg)
        results.append(result)
        print(f"  → coverage {result['covered']}/{result['total']} ({result['coverage_rate']*100:.1f}%)")
    return results


def main():
    all_results: list[dict] = []

    with multiprocessing.Pool(processes=len(APIS)) as pool:
        jobs = [pool.apply_async(run_api, (url, base)) for url, base in APIS]
        for job in jobs:
            all_results.extend(job.get())

    # Write CSV
    fieldnames = ["api", "config", "covered", "total", "coverage_rate", "elapsed_seconds", "error"]
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)

    print(f"\nAblation results written to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
