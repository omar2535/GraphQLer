# flake8: noqa
"""Dependency inference accuracy evaluation for GraphQLer.

Measures the precision, recall, and F1 score of GraphQLer's heuristic-based
dependency inference against manually annotated ground truth.

Two aspects are evaluated:
  1. Mutation type labeling accuracy (CREATE / UPDATE / DELETE / UNKNOWN)
  2. Dependency edge accuracy (hardDependsOn, softDependsOn)

Usage:
  # First compile the target APIs:
  python -m graphqler --mode compile --url <URL> --path <PATH>

  # Then run this script:
  python benchmark/benchmark_inference_accuracy.py

Results are written to benchmark/inference_accuracy_results.json.
"""

import json
import os
from pathlib import Path

import yaml

# ------------------------------------------------------------------
# APIs to evaluate: (api_url, compiled_output_path, ground_truth_file)
# ------------------------------------------------------------------
APIS = [
    (
        "https://countries.trevorblades.com/",
        "ablation/countries/full/",
        Path(__file__).parent / "ground_truth" / "countries.yml",
    ),
    (
        "https://rickandmortyapi.com/graphql",
        "ablation/rick-and-morty/full/",
        Path(__file__).parent / "ground_truth" / "rick_and_morty.yml",
    ),
    (
        "https://graphqlzero.almansi.me/api",
        "ablation/graphql-zero/full/",
        Path(__file__).parent / "ground_truth" / "graphql_zero.yml",
    ),
]

OUTPUT_JSON = Path(__file__).parent / "inference_accuracy_results.json"

# Compiled YAML file names (mirror graphqler/config.py)
COMPILED_DIR = "compiled"
COMPILED_MUTATIONS_FILE = "compiled_mutations.yml"
COMPILED_QUERIES_FILE = "compiled_queries.yml"


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _precision_recall_f1(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def evaluate_mutation_type(compiled_mutations: dict, gt_mutations: list) -> dict:
    """Compare heuristic mutationType labels against ground truth.

    Returns per-label metrics and an overall accuracy score.
    """
    total = 0
    correct = 0
    unknown_count = 0
    per_label = {"CREATE": {"tp": 0, "fp": 0, "fn": 0},
                 "UPDATE": {"tp": 0, "fp": 0, "fn": 0},
                 "DELETE": {"tp": 0, "fp": 0, "fn": 0},
                 "UNKNOWN": {"tp": 0, "fp": 0, "fn": 0}}
    details = []

    gt_map = {m["name"]: m for m in gt_mutations}

    for name, mutation_data in compiled_mutations.items():
        if name not in gt_map:
            continue
        predicted = mutation_data.get("mutationType", "UNKNOWN")
        expected = gt_map[name].get("mutationType", "UNKNOWN")
        total += 1
        if predicted == expected:
            correct += 1
        if predicted == "UNKNOWN":
            unknown_count += 1

        for label in per_label:
            if predicted == label and expected == label:
                per_label[label]["tp"] += 1
            elif predicted == label and expected != label:
                per_label[label]["fp"] += 1
            elif predicted != label and expected == label:
                per_label[label]["fn"] += 1

        details.append({"name": name, "predicted": predicted, "expected": expected, "correct": predicted == expected})

    accuracy = correct / total if total > 0 else 0.0
    unknown_rate = unknown_count / total if total > 0 else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "unknown_rate": round(unknown_rate, 4),
        "total_mutations_evaluated": total,
        "per_label_metrics": {label: _precision_recall_f1(v["tp"], v["fp"], v["fn"]) for label, v in per_label.items()},
        "details": details,
    }


def evaluate_dependencies(compiled_ops: dict, gt_ops: list, dep_key: str) -> dict:
    """Evaluate dependency edge precision/recall for hardDependsOn or softDependsOn.

    A predicted edge is a TP if it appears in ground truth, FP if not, FN if missed.
    """
    tp, fp, fn = 0, 0, 0
    gt_map = {op["name"]: set(op.get(dep_key, [])) for op in gt_ops}

    for name, op_data in compiled_ops.items():
        if name not in gt_map:
            continue
        predicted_deps = set(op_data.get(dep_key, []))
        expected_deps = gt_map[name]
        tp += len(predicted_deps & expected_deps)
        fp += len(predicted_deps - expected_deps)
        fn += len(expected_deps - predicted_deps)

    return _precision_recall_f1(tp, fp, fn)


# ------------------------------------------------------------------
# Main evaluation loop
# ------------------------------------------------------------------

def evaluate_api(api_url: str, output_path: str, gt_file: Path) -> dict:
    compiled_dir = Path(output_path) / COMPILED_DIR
    compiled_mutations_path = compiled_dir / COMPILED_MUTATIONS_FILE
    compiled_queries_path = compiled_dir / COMPILED_QUERIES_FILE

    if not compiled_dir.exists():
        return {"error": f"Compiled directory not found: {compiled_dir}. Run compile mode first."}

    compiled_mutations = _load_yaml(compiled_mutations_path)
    compiled_queries = _load_yaml(compiled_queries_path)
    ground_truth = _load_yaml(gt_file)

    gt_mutations = ground_truth.get("mutations", [])
    gt_queries = ground_truth.get("queries", [])

    result: dict = {"api": api_url}

    # 1. Mutation type labeling
    if gt_mutations:
        result["mutation_type_labeling"] = evaluate_mutation_type(compiled_mutations, gt_mutations)
    else:
        result["mutation_type_labeling"] = {"note": "No mutations in ground truth for this API"}

    # 2. Dependency edge accuracy (mutations)
    if gt_mutations and compiled_mutations:
        result["mutation_hard_depends_on"] = evaluate_dependencies(compiled_mutations, gt_mutations, "hardDependsOn")
        result["mutation_soft_depends_on"] = evaluate_dependencies(compiled_mutations, gt_mutations, "softDependsOn")
    else:
        result["mutation_hard_depends_on"] = {"note": "No mutation data available"}
        result["mutation_soft_depends_on"] = {"note": "No mutation data available"}

    # 3. Dependency edge accuracy (queries)
    if gt_queries and compiled_queries:
        result["query_hard_depends_on"] = evaluate_dependencies(compiled_queries, gt_queries, "hardDependsOn")
        result["query_soft_depends_on"] = evaluate_dependencies(compiled_queries, gt_queries, "softDependsOn")
    else:
        result["query_hard_depends_on"] = {"note": "No query data available"}
        result["query_soft_depends_on"] = {"note": "No query data available"}

    return result


def main():
    all_results = []
    for api_url, output_path, gt_file in APIS:
        print(f"Evaluating {api_url} ...")
        result = evaluate_api(api_url, output_path, gt_file)
        if "mutation_type_labeling" in result and "accuracy" in result["mutation_type_labeling"]:
            acc = result["mutation_type_labeling"]["accuracy"]
            unk = result["mutation_type_labeling"]["unknown_rate"]
            print(f"  Mutation type accuracy: {acc * 100:.1f}%  (UNKNOWN rate: {unk * 100:.1f}%)")
        all_results.append(result)

    with open(OUTPUT_JSON, "w") as f:
        json.dump(all_results, f, indent=4)
    print(f"\nInference accuracy results written to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
