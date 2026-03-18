"""ResolverComparison — aggregates and persists the side-by-side comparison of
LLM resolver output vs classic resolver output.

The saved JSON file (`eval/resolver_comparison.json`) is structured to make
systematic analysis easy:

{
  "summary": {
    "total_mutations": int,
    "mutations_that_differ": int,
    "total_queries": int,
    "queries_that_differ": int
  },
  "mutations": {
    "<name>": {
      "classic": {"mutationType": "...", "hardDependsOn": {...}, "softDependsOn": {...}},
      "llm":     {"mutationType": "...", "hardDependsOn": {...}, "softDependsOn": {...}},
      "differs": bool,
      "diff": { "<field>": {"classic": ..., "llm": ...} }
    }
  },
  "queries": { ... same shape without mutationType ... }
}
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

COMPARISON_FILE_NAME = "eval/resolver_comparison.json"


class ResolverComparison:
    """Holds and saves the LLM-vs-classic comparison for mutations and queries."""

    def __init__(self, mutation_comparison: dict, query_comparison: dict):
        """
        Args:
            mutation_comparison (dict): Output of LLMMutationObjectResolver.comparison.
            query_comparison (dict): Output of LLMQueryObjectResolver.comparison.
        """
        self.mutation_comparison = mutation_comparison
        self.query_comparison = query_comparison

    def build(self) -> dict:
        """Build the full comparison document.

        Returns:
            dict: The complete comparison document with summary + per-endpoint diffs.
        """
        mutations_that_differ = sum(1 for v in self.mutation_comparison.values() if v.get("differs"))
        queries_that_differ = sum(1 for v in self.query_comparison.values() if v.get("differs"))

        return {
            "summary": {
                "total_mutations": len(self.mutation_comparison),
                "mutations_that_differ": mutations_that_differ,
                "total_queries": len(self.query_comparison),
                "queries_that_differ": queries_that_differ,
            },
            "mutations": self.mutation_comparison,
            "queries": self.query_comparison,
        }

    def save(self, output_dir: str) -> str:
        """Serialize and write the comparison document to disk.

        Args:
            output_dir (str): The run output directory (same as the compiled/ parent).

        Returns:
            str: Absolute path of the written file.
        """
        dest = Path(output_dir) / COMPARISON_FILE_NAME
        dest.parent.mkdir(parents=True, exist_ok=True)
        document = self.build()
        with open(dest, "w") as f:
            json.dump(document, f, indent=2)
        logger.info(f"Resolver comparison saved to {dest}")
        summary = document["summary"]
        print(
            f"(C) LLM resolver comparison: "
            f"{summary['mutations_that_differ']}/{summary['total_mutations']} mutations differ, "
            f"{summary['queries_that_differ']}/{summary['total_queries']} queries differ  →  {dest}"
        )
        return str(dest)

    def print_diff_summary(self):
        """Print a human-readable diff summary to stdout."""
        doc = self.build()
        summary = doc["summary"]
        print(f"\n{'='*60}")
        print("  Resolver comparison: LLM vs Classic")
        print(f"{'='*60}")
        print(f"  Mutations : {summary['mutations_that_differ']} / {summary['total_mutations']} differ")
        print(f"  Queries   : {summary['queries_that_differ']} / {summary['total_queries']} differ")

        for section, label in (("mutations", "MUTATION"), ("queries", "QUERY")):
            for name, entry in doc[section].items():
                if not entry.get("differs"):
                    continue
                print(f"\n  [{label}] {name}")
                for field, values in entry.get("diff", {}).items():
                    print(f"    {field}:")
                    print(f"      classic: {values['classic']}")
                    print(f"      llm    : {values['llm']}")
        print(f"{'='*60}\n")
