"""Heuristic-based classifier for identifying UAF candidate chains.

A chain is a UAF (use-after-free / use-after-delete) candidate when:
  1. At least one CREATE mutation establishes a resource.
  2. A subsequent DELETE mutation removes that resource.
  3. At least one later node (Query or non-DELETE Mutation) attempts to
     access the same resource — something the API should reject for a
     properly invalidated resource.

Scoring
-------
Three independent signals each contribute to a confidence value in [0, 1].
The classifier evaluates *every* post-delete node and uses the highest-scoring
one to avoid penalising chains with intermediate Object nodes.

  +0.5 — Type match: the CREATE output type matches an input parameter type
          of the post-delete test node. This proves a direct data dependency
          on the deleted resource.

  +0.3 — Access pattern: the test node name contains single-item-access tokens
          (get, fetch, find, read, view …) and does NOT contain list tokens
          (list, all, search …). This indicates the operation is likely
          fetching a specific resource by ID rather than browsing a collection.

  +0.2 — ID parameter presence: the test node accepts an ID or Int scalar input.

The ``split_index`` is placed immediately after the last DELETE mutation.
"""

from __future__ import annotations

import re
from graphqler.chains.chain import Chain
from graphqler.graph.node import Node


# ── Keyword tables ────────────────────────────────────────────────────────────

_SINGLE_ACCESS_TOKENS: frozenset[str] = frozenset({
    "get", "fetch", "find", "read", "view", "show", "detail", "details",
    "retrieve", "load", "single", "one", "item", "by",
})

_LIST_ACCESS_TOKENS: frozenset[str] = frozenset({
    "list", "all", "search", "browse", "explore", "discover",
    "many", "multiple", "batch", "bulk", "paginate", "paginated",
})


def _tokenize(name: str) -> list[str]:
    """Split camelCase / snake_case name into lowercase tokens."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    return [t.lower() for t in re.split(r"[^a-zA-Z0-9]+", spaced) if t]


def _resolve_output_type(node: Node) -> str | None:
    """Return the primary object output type of a CREATE node, or None."""
    body = node.body or {}
    output = body.get("output")
    if isinstance(output, dict):
        t = output.get("name") or output.get("type")
        if t:
            return t
    for key in ("outputType", "output_type", "type"):
        val = body.get(key)
        if isinstance(val, str) and val:
            return val
        if isinstance(val, dict):
            return val.get("name") or val.get("type")
    return None


def _collect_input_type_names(node: Node) -> set[str]:
    """Return all named types referenced in the node's input parameters."""
    body = node.body or {}
    inputs = body.get("inputs", {}) or body.get("parameters", {}) or {}
    result: set[str] = set()

    def _walk(info):
        if info is None:
            return
        if isinstance(info, dict):
            type_info = info.get("type")
            if isinstance(type_info, str):
                result.add(type_info)
            elif isinstance(type_info, dict):
                _walk(type_info)
            _walk(info.get("ofType"))

    for field_info in inputs.values():
        _walk(field_info)

    # Also include types listed in hardDependsOn — the compiler resolves these
    hard = body.get("hardDependsOn") or {}
    result.update(v for v in hard.values() if isinstance(v, str))

    return result


def _has_id_input(node: Node) -> bool:
    """Return True if the node has at least one Int or ID scalar input parameter."""
    body = node.body or {}
    inputs = body.get("inputs", {}) or body.get("parameters", {}) or {}

    def _scalar_type(info) -> str | None:
        if info is None:
            return None
        if isinstance(info, dict):
            if info.get("kind") == "SCALAR":
                return info.get("type")
            return _scalar_type(info.get("ofType"))
        return None

    for field_info in inputs.values():
        if _scalar_type(field_info) in ("Int", "ID"):
            return True
    # Also consider hardDependsOn as an implicit ID dependency
    hard = body.get("hardDependsOn") or {}
    return bool(hard)


def _score_test_node(test_node: Node, create_output: str | None) -> tuple[float, list[str]]:
    """Compute heuristic score for a single candidate post-delete test node."""
    confidence = 0.0
    reasons: list[str] = []

    # Signal 1: type-match (+0.5) — proves the node accesses the created/deleted type
    if create_output:
        test_inputs = _collect_input_type_names(test_node)
        create_lower = create_output.lower()
        for t in test_inputs:
            if t and (create_lower == t.lower() or create_lower in t.lower() or t.lower() in create_lower):
                confidence += 0.5
                reasons.append(f"type-match: CREATE/DELETE type '{create_output}' ↔ test inputs '{t}'")
                break

    # Signal 2: access-pattern heuristic (+0.3 / -0.2)
    test_tokens = set(_tokenize(test_node.name))
    access_hits = test_tokens & _SINGLE_ACCESS_TOKENS
    list_hits = test_tokens & _LIST_ACCESS_TOKENS
    if access_hits and not list_hits:
        confidence += 0.3
        reasons.append(f"access-pattern: single-access tokens {access_hits}")
    elif list_hits:
        confidence = max(0.0, confidence - 0.2)
        reasons.append(f"access-pattern penalty: list tokens {list_hits}")

    # Signal 3: ID/Int parameter (+0.2)
    if _has_id_input(test_node):
        confidence += 0.2
        reasons.append("id-param: test node accepts ID/Int input")

    return confidence, reasons


# ── Public API ────────────────────────────────────────────────────────────────

def classify(chain: Chain) -> tuple[float, int, str]:
    """Score a chain for UAF candidate likelihood using heuristics.

    Evaluates every node after the DELETE split, taking the best-scoring
    Query or non-DELETE Mutation node.  This avoids penalising chains where
    intermediate Object nodes sit between the DELETE and the actual test
    operation.

    Args:
        chain: The compiled chain to evaluate.

    Returns:
        A tuple of ``(confidence, split_index, reason)`` where:
          - ``confidence`` is in [0.0, 1.0].
          - ``split_index`` is the index of the first post-delete node (executed
            after the DELETE mutation step).
          - ``reason`` is a human-readable explanation of the score.
    """
    steps = chain.steps

    if len(steps) < 3:
        return 0.0, 0, "chain too short (need at least 3 nodes: CREATE, DELETE, ACCESS)"

    # Find the last DELETE mutation
    last_delete_idx: int | None = None
    for i, step in enumerate(steps):
        if step.node.graphql_type == "Mutation" and step.node.mutation_type == "DELETE":
            last_delete_idx = i

    if last_delete_idx is None:
        return 0.0, 0, "no DELETE mutation in chain"

    split_index = last_delete_idx + 1
    if split_index >= len(steps):
        return 0.0, 0, "DELETE mutation is the last node — nothing to test after deletion"

    # Ensure there is a CREATE before the DELETE
    create_before_delete: Node | None = None
    for i in range(last_delete_idx):
        if steps[i].node.graphql_type == "Mutation" and steps[i].node.mutation_type == "CREATE":
            create_before_delete = steps[i].node

    if create_before_delete is None:
        return 0.0, 0, "no CREATE mutation before the DELETE in chain"

    create_output = _resolve_output_type(create_before_delete)

    # Evaluate every post-delete node; keep the best-scoring Query or non-DELETE Mutation
    best_conf = 0.0
    best_reasons: list[str] = []

    for step in steps[split_index:]:
        test_node = step.node
        if test_node.graphql_type not in ("Query", "Mutation"):
            continue
        if test_node.mutation_type == "DELETE":
            continue  # Another DELETE is not a meaningful UAF test
        conf, reasons = _score_test_node(test_node, create_output)
        if conf > best_conf:
            best_conf = conf
            best_reasons = reasons

    if best_conf == 0.0:
        return 0.0, split_index, "no signals matched"

    return min(best_conf, 1.0), split_index, "; ".join(best_reasons)
