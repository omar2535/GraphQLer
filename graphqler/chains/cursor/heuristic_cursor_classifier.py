"""Heuristic classifier for identifying pagination query nodes.

A node is considered a pagination endpoint when its input arguments or return
type match well-known Relay / offset-based pagination patterns.

Scoring
-------
Signals are evaluated independently and the highest applicable score is used
(signals are not additive):

  0.9 — Node already annotated with ``pagination.style == "relay"``
        (set by :class:`~graphqler.compiler.parsers.QueryListParser`).

  0.85 — Both cursor arg (``after``/``before``) AND size arg (``first``/``last``)
         present — the classic Relay combo.

  0.7 — Input arg named ``after`` or ``before`` (relay cursor args).

  0.5 — Return type name ends with ``"Connection"``.

  0.4 — Input arg named ``cursor`` (non-Relay cursor arg).

  0.3 — Input args include ``first``/``last`` (Relay size args only).

  0.2 — Input arg named ``offset``, ``page``, or ``skip`` (offset-style).
"""

from __future__ import annotations

from graphqler.graph.node import Node


# ── Keyword sets ───────────────────────────────────────────────────────────────

_RELAY_CURSOR_ARGS: frozenset[str] = frozenset({"after", "before"})
_RELAY_SIZE_ARGS: frozenset[str] = frozenset({"first", "last"})
_GENERIC_CURSOR_ARGS: frozenset[str] = frozenset({"cursor"})
_OFFSET_ARGS: frozenset[str] = frozenset({"offset", "page", "skip"})


# ── Public API ─────────────────────────────────────────────────────────────────

def classify(node: Node) -> tuple[float, str]:
    """Rate a Query node as a pagination endpoint.

    Args:
        node: The graph node to evaluate.  Non-Query nodes always score 0.

    Returns:
        ``(confidence, reason)`` where *confidence* ∈ [0.0, 1.0] and *reason*
        is a human-readable description of the signals found.
    """
    if node.graphql_type != "Query":
        return 0.0, "not a Query node"

    body = node.body or {}
    confidence = 0.0
    reasons: list[str] = []

    # ── Compiler annotation (highest priority) ─────────────────────────────────
    pagination = body.get("pagination") or {}
    if pagination.get("style") == "relay":
        confidence = max(confidence, 0.9)
        reasons.append("relay-annotation: compiler detected Relay-style pagination")

    # ── Input-arg signals ──────────────────────────────────────────────────────
    inputs = body.get("inputs") or {}
    arg_names_lower: set[str] = {k.lower() for k in inputs}

    has_relay_cursor = bool(arg_names_lower & _RELAY_CURSOR_ARGS)
    has_relay_size = bool(arg_names_lower & _RELAY_SIZE_ARGS)

    if has_relay_cursor and has_relay_size:
        confidence = max(confidence, 0.85)
        reasons.append(
            f"relay-combo: cursor arg {arg_names_lower & _RELAY_CURSOR_ARGS}"
            f" + size arg {arg_names_lower & _RELAY_SIZE_ARGS}"
        )
    elif has_relay_cursor:
        confidence = max(confidence, 0.7)
        reasons.append(f"cursor-arg: {arg_names_lower & _RELAY_CURSOR_ARGS}")

    if has_relay_size and not has_relay_cursor:
        confidence = max(confidence, 0.3)
        reasons.append(f"size-arg: {arg_names_lower & _RELAY_SIZE_ARGS}")

    if arg_names_lower & _GENERIC_CURSOR_ARGS and not has_relay_cursor:
        confidence = max(confidence, 0.4)
        reasons.append("cursor-arg: generic 'cursor' parameter found")

    if arg_names_lower & _OFFSET_ARGS:
        confidence = max(confidence, 0.2)
        reasons.append(f"offset-arg: {arg_names_lower & _OFFSET_ARGS}")

    # ── Return-type name signal ────────────────────────────────────────────────
    return_type_name = _resolve_return_type_name(body)
    if return_type_name and return_type_name.endswith("Connection"):
        confidence = max(confidence, 0.5)
        reasons.append(f"connection-type: return type '{return_type_name}' ends with 'Connection'")

    if not reasons:
        return 0.0, "no pagination signals detected"

    return min(confidence, 1.0), "; ".join(reasons)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _resolve_return_type_name(body: dict) -> str | None:
    """Walk the ``output`` / ``ofType`` chain to find the concrete type name."""
    output = body.get("output") or {}
    name = output.get("name") or output.get("type")
    if name:
        return name
    # Unwrap NON_NULL / LIST wrappers
    of_type = output.get("ofType")
    while isinstance(of_type, dict):
        name = of_type.get("name") or of_type.get("type")
        if name:
            return name
        of_type = of_type.get("ofType")
    return None
