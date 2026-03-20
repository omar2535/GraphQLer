# GraphQLer Benchmarks

This directory contains scripts for evaluating and comparing GraphQLer across different
configurations, APIs, and components. Each script targets a specific research question.

---

## Scripts

### `benchmark_odg.py` — Out-of-the-box (full pipeline)

Runs GraphQLer's full compile + fuzz pipeline against a set of public APIs with the
dependency graph enabled. This is the primary script used to produce the main results
table in the paper (operation coverage across real-world APIs).

**What it measures:** operation coverage rate (successful operations / total operations)
per API under a fixed time budget.

**Output:** per-run `stats.json` and `run_metadata.json` saved under each API's output
directory; prints live progress to stdout.

**Configure:** edit `APIS_TO_TEST` and `MAX_TIMES` at the top of the file.

```bash
uv run python benchmark/benchmark_odg.py
```

---

### `benchmark_oob.py` — Objects-bucket only (no dependency graph)

Same as `benchmark_odg.py` but with `USE_DEPENDENCY_GRAPH=False` and
`USE_OBJECTS_BUCKET=True`. Useful as an isolated baseline to measure the contribution
of the objects bucket independently of the dependency graph.

**Configure:** edit `APIS_TO_TEST` and `MAX_TIMES`.

```bash
uv run python benchmark/benchmark_oob.py
```

---

### `benchmark_ablation.py` — Ablation study

Runs all four configuration combinations across a set of APIs to isolate the
contribution of each component:

| Config | `USE_DEPENDENCY_GRAPH` | `USE_OBJECTS_BUCKET` |
|---|---|---|
| `baseline` | ✗ | ✗ |
| `graph_only` | ✓ | ✗ |
| `bucket_only` | ✗ | ✓ |
| `full` | ✓ | ✓ |

**What it measures:** operation coverage per API per config — produces the ablation
table used in the paper.

**Output:** `ablation_results.csv` written alongside this script.

**Configure:** edit `APIS` at the top of the file.

```bash
uv run python benchmark/benchmark_ablation.py
```

---

### `benchmark_inference_accuracy.py` — Dependency inference accuracy

Measures the precision, recall, and F1 of GraphQLer's heuristic dependency inference
against manually annotated ground truth files (in `ground_truth/`).

**What it measures:**
- Mutation type labeling accuracy (CREATE / UPDATE / DELETE / UNKNOWN)
- Dependency edge accuracy (`hardDependsOn`, `softDependsOn`)

**Requires:** compiled output from a prior `compile` run. The script reads from the
`full/` config paths produced by `benchmark_ablation.py` by default, or you can point
`APIS` at any compiled output directory.

**Output:** `benchmark/inference_accuracy_results.json`.

```bash
# Step 1: run ablation to produce compiled output
uv run python benchmark/benchmark_ablation.py

# Step 2: evaluate inference accuracy
uv run python benchmark/benchmark_inference_accuracy.py
```

Ground truth files live in `ground_truth/`:
- `countries.yml` — Countries API (queries only)
- `rick_and_morty.yml` — Rick & Morty API (queries only)
- `graphql_zero.yml` — GraphQL Zero API (queries + CRUD mutations with dependency annotations)

---

### `benchmark_llm_chains.py` — LLM vs heuristic chain generation

Compares GraphQLer's heuristic dependency chain generation against an LLM-assisted
version for a user-specified set of APIs. Specifically benchmarks the `compile-chains`
component.

> **Note:** This script benchmarks only the chain-generation component. Future
> `benchmark_llm_*.py` scripts will cover other LLM-assisted components (e.g. payload
> generation, response analysis).

**What it measures:** chain count, average chain length, max chain length, total nodes
covered — for heuristic and LLM side by side.

**Output:**
- `<output>/<api-name>/heuristic/compiled/chains.yml`
- `<output>/<api-name>/llm/compiled/chains.yml`
- `<output>/llm_chains_results.json`

```bash
# Ollama (local model):
uv run python benchmark/benchmark_llm_chains.py \
    --output /tmp/llm-chains \
    --llm-model ollama/gpt-oss:20b \
    --llm-base-url http://localhost:11434 \
    --apis http://localhost:4000/graphql:food-delivery \
           http://localhost:4001/graphql:user-wallet

# OpenAI:
uv run python benchmark/benchmark_llm_chains.py \
    --output /tmp/llm-chains \
    --llm-model gpt-4o-mini \
    --llm-api-key sk-... \
    --apis https://rickandmortyapi.com/graphql:rick-and-morty

# Query chains only (no mutations):
uv run python benchmark/benchmark_llm_chains.py \
    --output /tmp/llm-chains \
    --disable-mutations \
    --apis http://localhost:4000/graphql:food-delivery
```

**Arguments:**

| Argument | Description |
|---|---|
| `--output` / `-o` | Directory to save all run output and results JSON (required) |
| `--apis URL:NAME ...` | One or more APIs in `URL:NAME` format (required) |
| `--llm-model` | litellm model string (default: `gpt-4o-mini`) |
| `--llm-base-url` | Custom base URL for Ollama / LiteLLM proxies |
| `--llm-api-key` | API key (or set `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` env var) |
| `--llm-max-retries` | Retries when LLM returns non-JSON (default: 2) |
| `--disable-mutations` | Only generate Query chains |

---

## Directory structure

```
benchmark/
├── benchmark_odg.py                  # Full pipeline — main results table
├── benchmark_oob.py                  # Objects-bucket-only baseline
├── benchmark_ablation.py             # 4-config ablation study
├── benchmark_inference_accuracy.py   # Dependency inference precision/recall
├── benchmark_llm_chains.py           # LLM vs heuristic chain generation
├── ground_truth/
│   ├── countries.yml
│   ├── rick_and_morty.yml
│   └── graphql_zero.yml
└── readme.md
```
