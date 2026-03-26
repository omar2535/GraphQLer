"""Cursor encoding/decoding and mutation utilities for pagination security testing.

Provides pure functions to:
* Decode opaque cursor strings (base64+JSON, plain base64, or raw strings).
* Re-encode mutated payloads back into the same format.
* Extract live cursor values from a GraphQL response dict.
* Produce IDOR-probe variants (integer-field shifts).
* Produce injection-probe variants (SQL / NoSQL / path-traversal payloads).
"""

from __future__ import annotations

import base64
import json


# ── Cursor field names typically returned by paginated queries ─────────────────

_CURSOR_KEYS: frozenset[str] = frozenset({"endCursor", "startCursor", "cursor"})

# ── Injection payload banks ───────────────────────────────────────────────────

_SQL_PAYLOADS: list[str] = [
    "' OR '1'='1",
    "' OR 1=1--",
    "'; DROP TABLE users;--",
    "1 AND SLEEP(3)--",
    "1; SELECT pg_sleep(3)--",
]

_NOSQL_PAYLOADS: list[str] = [
    '{"$where": "sleep(100)"}',
    '{"$gt": ""}',
]

_PATH_PAYLOADS: list[str] = [
    "../../etc/passwd",
    "..\\..\\windows\\system32\\drivers\\etc\\hosts",
]


# ── Decode / encode ────────────────────────────────────────────────────────────

def decode_cursor(cursor_str: str) -> dict | str:
    """Base64-decode and JSON-parse an opaque cursor string.

    Tries standard base64, URL-safe base64, and both with/without padding.
    Returns the original *cursor_str* unchanged if decoding fails entirely.

    Args:
        cursor_str: The opaque pagination cursor to decode.

    Returns:
        A ``dict`` if the decoded value is valid JSON, a plain ``str`` if the
        base64 decodes but is not JSON, or *cursor_str* as-is on failure.
    """
    padded = cursor_str + "=" * (-len(cursor_str) % 4)
    for variant in (padded, cursor_str):
        for decode_fn in (base64.b64decode, base64.urlsafe_b64decode):
            try:
                decoded_bytes = decode_fn(variant)
                decoded_str = decoded_bytes.decode("utf-8", errors="strict")
                try:
                    return json.loads(decoded_str)
                except (json.JSONDecodeError, ValueError):
                    return decoded_str
            except Exception:
                continue
    return cursor_str


def encode_cursor(data: dict | str) -> str:
    """Encode data into a base64 cursor string.

    Dicts are JSON-serialised before encoding; strings are encoded directly.

    Args:
        data: A ``dict`` (serialised to compact JSON first) or a raw string.

    Returns:
        A standard (non-URL-safe) base64-encoded cursor string.
    """
    if isinstance(data, dict):
        raw = json.dumps(data, separators=(",", ":"))
    else:
        raw = str(data)
    return base64.b64encode(raw.encode("utf-8")).decode("ascii")


# ── Response scanning ──────────────────────────────────────────────────────────

def extract_cursor_from_response(response_data: dict) -> list[str]:
    """Recursively scan a GraphQL response dict for cursor values.

    Looks for keys named ``endCursor``, ``startCursor``, or ``cursor`` and
    returns all non-null, non-empty string values found anywhere in the tree.

    Args:
        response_data: The ``data`` sub-dict from a GraphQL response.

    Returns:
        A list of discovered cursor strings (may be empty).
    """
    found: list[str] = []

    def _walk(obj: object) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in _CURSOR_KEYS and isinstance(value, str) and value:
                    found.append(value)
                else:
                    _walk(value)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(response_data)
    return found


# ── Mutation helpers ───────────────────────────────────────────────────────────

def mutate_for_idor(cursor_str: str) -> list[str]:
    """Return cursor variants with integer fields shifted to probe cross-user access.

    Decodes the cursor, then for every integer-valued field produces variants
    where that field is replaced with ``original ± 1``, ``original × 2``,
    ``0``, and ``9999``.  Each variant is re-encoded and returned as a
    deduplicated list (the original cursor is excluded).

    Args:
        cursor_str: An opaque cursor string (typically base64-encoded JSON).

    Returns:
        A list of mutated cursor strings ready to use as ``after``/``before``
        argument values.  Falls back to ``[cursor_str]`` if the cursor cannot
        be decoded into a dict with integer fields.
    """
    decoded = decode_cursor(cursor_str)
    if not isinstance(decoded, dict):
        return [cursor_str]

    integer_fields = {k: v for k, v in decoded.items() if isinstance(v, int)}
    if not integer_fields:
        return [cursor_str]

    mutants: list[str] = []
    for field, original_value in integer_fields.items():
        for mutated_value in (
            original_value + 1,
            original_value - 1,
            original_value * 2,
            0,
            9999,
        ):
            variant = dict(decoded)
            variant[field] = mutated_value
            mutants.append(encode_cursor(variant))

    seen: set[str] = set()
    unique: list[str] = []
    for m in mutants:
        if m not in seen and m != cursor_str:
            seen.add(m)
            unique.append(m)
    return unique or [cursor_str]


def mutate_for_injection(cursor_str: str) -> list[str]:
    """Return cursor variants with injection payloads embedded in string fields.

    Decodes the cursor and replaces every string-valued field with each payload
    from the SQL, NoSQL, and path-traversal banks.  If the decoded cursor has no
    string fields, raw payloads are encoded and returned directly.

    Args:
        cursor_str: An opaque cursor string.

    Returns:
        A deduplicated list of mutated cursor strings containing injection
        payloads.  Falls back to ``[cursor_str]`` if no variants can be built.
    """
    all_payloads: list[str] = _SQL_PAYLOADS + _NOSQL_PAYLOADS + _PATH_PAYLOADS
    decoded = decode_cursor(cursor_str)
    variants: list[str] = []

    if isinstance(decoded, dict):
        string_fields = [k for k, v in decoded.items() if isinstance(v, str)]
        if string_fields:
            for field in string_fields:
                for payload in all_payloads:
                    variant = dict(decoded)
                    variant[field] = payload
                    variants.append(encode_cursor(variant))
        else:
            for payload in all_payloads:
                variants.append(encode_cursor(payload))
    else:
        for payload in all_payloads:
            variants.append(encode_cursor(payload))

    seen: set[str] = set()
    unique: list[str] = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            unique.append(v)
    return unique or [cursor_str]
