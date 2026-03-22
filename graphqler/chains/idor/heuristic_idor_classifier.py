"""Heuristic-based classifier for identifying IDOR candidate chains.

A chain is an IDOR candidate when:
  1. At least one CREATE mutation produces an object (the "setup").
  2. At least one later node (Query or UPDATE/DELETE mutation) consumes that
     object's ID — meaning a different user could potentially access it.

Scoring
-------
Three independent signals each contribute to a confidence value in [0, 1].
The classifier evaluates *every* test node after the split and uses the
highest-scoring node rather than only the first one, because chains often
contain intermediate Object nodes before the interesting Query/Mutation.

  +0.5 — Type match: the output type (or hardDependsOn type) of a CREATE node
          matches an input parameter type / hardDependsOn value of a test node.
          This is the strongest signal because it proves a direct data dependency.

  +0.3 — Name heuristic: the test node name contains ownership-scoped keywords
          (user, my, profile, order …) and does NOT contain public catalogue
          keywords (list, all, public …).

  +0.2 — ID parameter presence: the test node accepts an ID or Int scalar input.

The ``split_index`` is placed immediately after the last CREATE mutation.
"""

from __future__ import annotations

import re
from graphqler.chains.chain import Chain
from graphqler.graph.node import Node


# ── Keyword tables ────────────────────────────────────────────────────────────

_PRIVATE_TOKENS: frozenset[str] = frozenset({
    "user", "users", "account", "accounts", "profile", "profiles",
    "me", "my", "own", "self", "personal", "private",
    "permission", "permissions", "role", "roles",
    "session", "sessions", "token", "tokens",
    "order", "orders", "invoice", "invoices", "payment", "payments",
    "transaction", "transactions", "subscription", "subscriptions",
    "billing", "cart", "checkout", "wallet",
    "ticket", "tickets", "task", "tasks",
    "note", "notes",
    "message", "messages", "chat", "notification", "notifications", "inbox",
    "patient", "patients", "medical", "employee", "employees",
    "customer", "customers", "client", "clients",
    "owned", "mine", "favourites", "favorites", "wishlist",
})

_PUBLIC_TOKENS: frozenset[str] = frozenset({
    "book", "books", "product", "products", "item", "items",
    "post", "posts", "article", "articles", "blog", "news",
    "event", "events", "category", "categories", "tag", "tags",
    "movie", "movies", "film", "films", "show", "shows",
    "song", "songs", "album", "albums", "track", "tracks",
    "photo", "photos", "image", "images", "video", "videos",
    "restaurant", "restaurants", "store", "stores",
    "location", "locations", "public", "shared", "global",
    "catalog", "catalogue", "search", "browse", "explore", "discover",
    "menu", "listing", "listings", "directory",
    "list", "all",
})


def _tokenize(name: str) -> list[str]:
    """Split camelCase / snake_case name into lowercase tokens."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    return [t.lower() for t in re.split(r"[^a-zA-Z0-9]+", spaced) if t]


def _resolve_output_type(node: Node) -> str | None:
    """Return the primary object output type of a CREATE node, or None."""
    body = node.body or {}
    # Check the `output` dict that the compiler stores for all query/mutation nodes
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
            if info.get("kind") in ("OBJECT", "INPUT_OBJECT", "SCALAR") and info.get("type"):
                result.add(info["type"])
            if info.get("name"):
                result.add(info["name"])
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
    hard = (body.get("hardDependsOn") or {})
    return bool(hard)


def _score_test_node(test_node: Node, create_output: str | None) -> tuple[float, list[str]]:
    """Compute heuristic score for a single candidate test node."""
    confidence = 0.0
    reasons: list[str] = []

    # Signal 1: type-match (+0.5)
    if create_output:
        test_inputs = _collect_input_type_names(test_node)
        create_lower = create_output.lower()
        for t in test_inputs:
            if t and (create_lower == t.lower() or create_lower in t.lower() or t.lower() in create_lower):
                confidence += 0.5
                reasons.append(f"type-match: CREATE outputs '{create_output}' ↔ test inputs '{t}'")
                break

    # Signal 2: name heuristic (+0.3 / -0.2)
    test_tokens = set(_tokenize(test_node.name))
    private_hits = test_tokens & _PRIVATE_TOKENS
    public_hits = test_tokens & _PUBLIC_TOKENS
    if private_hits and not public_hits:
        confidence += 0.3
        reasons.append(f"name-heuristic: private tokens {private_hits}")
    elif public_hits:
        confidence = max(0.0, confidence - 0.2)
        reasons.append(f"name-heuristic penalty: public tokens {public_hits}")

    # Signal 3: ID/Int parameter (+0.2)
    if _has_id_input(test_node):
        confidence += 0.2
        reasons.append("id-param: test node accepts ID/Int input")

    return confidence, reasons


# ── Public API ────────────────────────────────────────────────────────────────

def classify(chain: Chain) -> tuple[float, int, str]:
    """Score a chain for IDOR candidate likelihood using heuristics.

    Evaluates every node after the CREATE split, taking the best-scoring
    Query or Mutation node.  This avoids penalising chains where intermediate
    Object nodes sit between the CREATE and the actual test operation.

    Args:
        chain: The compiled chain to evaluate.

    Returns:
        A tuple of ``(confidence, split_index, reason)`` where:
          - ``confidence`` is in [0.0, 1.0].
          - ``split_index`` is the index of the first "test" node (executed
            with the secondary / attacker token).
          - ``reason`` is a human-readable explanation of the score.
    """
    nodes = chain.nodes

    if len(nodes) < 2:
        return 0.0, 0, "chain too short (need at least 2 nodes)"

    # Find the last CREATE mutation
    last_create_idx: int | None = None
    for i, node in enumerate(nodes):
        if node.graphql_type == "Mutation" and node.mutation_type == "CREATE":
            last_create_idx = i

    if last_create_idx is None:
        return 0.0, 0, "no CREATE mutation in chain"

    split_index = last_create_idx + 1
    if split_index >= len(nodes):
        return 0.0, 0, "CREATE mutation is the last node — nothing to test"

    create_node = nodes[last_create_idx]
    create_output = _resolve_output_type(create_node)

    # Evaluate every test node; keep the best-scoring Query or Mutation
    best_conf = 0.0
    best_reasons: list[str] = []

    for test_node in nodes[split_index:]:
        if test_node.graphql_type not in ("Query", "Mutation"):
            continue
        conf, reasons = _score_test_node(test_node, create_output)
        if conf > best_conf:
            best_conf = conf
            best_reasons = reasons

    if best_conf == 0.0:
        return 0.0, split_index, "no signals matched"

    return min(best_conf, 1.0), split_index, "; ".join(best_reasons)
