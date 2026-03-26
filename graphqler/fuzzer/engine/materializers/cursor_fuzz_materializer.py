"""CursorFuzzMaterializer: builds payloads with mutated cursor arguments.

Used exclusively in pagination-attack chains where step 2 re-submits the same
query with the cursor argument (``after``, ``before``, ``cursor``, …) replaced
by a decoded-mutated-re-encoded variant to probe injection or IDOR weaknesses.
"""

from __future__ import annotations

import random

from graphqler.config import MAX_INPUT_DEPTH, MAX_OUTPUT_SELECTOR_DEPTH
from graphqler.utils.api import API
from graphqler.utils.objects_bucket import ObjectsBucket

from .regular_payload_materializer import RegularPayloadMaterializer
from .utils.materialization_utils import prettify_graphql_payload
from graphqler.chains.cursor import cursor_utils


#: Input-argument names that carry a pagination cursor.
_CURSOR_ARG_NAMES: frozenset[str] = frozenset({"after", "before", "cursor"})

#: Keys that the scalars bucket may contain after a pagination query runs.
_CURSOR_SCALAR_KEYS: frozenset[str] = frozenset({"endCursor", "startCursor", "cursor"})


class CursorFuzzMaterializer(RegularPayloadMaterializer):
    """Extends :class:`RegularPayloadMaterializer` to inject mutated cursors.

    When materializing the cursor argument of a pagination query this
    materializer:

    1. Looks up all captured cursor strings in ``objects_bucket.scalars``
       (keys ``endCursor``, ``startCursor``, and ``cursor``).
    2. Picks one at random.
    3. Applies :func:`~graphqler.chains.cursor.cursor_utils.mutate_for_injection`
       or :func:`~graphqler.chains.cursor.cursor_utils.mutate_for_idor`
       depending on *fuzz_mode*.
    4. Uses the first mutated variant as the cursor argument value.

    If no cursor is available in the bucket, the materializer falls back to the
    standard random-value path so the chain still exercises the query.

    Args:
        api: The API descriptor.
        fuzz_mode: ``"injection"`` (SQL/NoSQL/path-traversal payloads) or
            ``"idor"`` (integer-field shifts for cross-user probing).
    """

    def __init__(self, api: API, fuzz_mode: str = "injection") -> None:
        super().__init__(api, fail_on_hard_dependency_not_met=False)
        self.fuzz_mode = fuzz_mode

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_payload(
        self,
        name: str,
        objects_bucket: ObjectsBucket,
        graphql_type: str,
        minimal_materialization: bool = False,
    ) -> tuple[str, dict]:
        """Materialise a query payload with the cursor arg replaced by a fuzz variant.

        Args:
            name: Query name.
            objects_bucket: Bucket from the setup (primary) step; should contain
                captured cursor scalars.
            graphql_type: Must be ``"Query"`` for cursor fuzzing; falls back to
                base class for any other type.
            minimal_materialization: Forwarded to the output materialiser.

        Returns:
            A ``(payload_string, used_objects)`` tuple.
        """
        self.used_objects = {}

        if graphql_type != "Query":
            return super().get_payload(name, objects_bucket, graphql_type)

        query_info = self.api.queries[name]

        # Resolve the cursor arg name (from compiler annotation or by scanning inputs)
        cursor_arg_name = self._resolve_cursor_arg(query_info)
        fuzzed_cursor = self._pick_fuzzed_cursor(objects_bucket)

        if cursor_arg_name and fuzzed_cursor:
            query_inputs = self._materialize_inputs_with_cursor(
                query_info, objects_bucket, cursor_arg_name, fuzzed_cursor
            )
        else:
            query_inputs = self.materialize_inputs(
                query_info, query_info["inputs"], objects_bucket, max_depth=MAX_INPUT_DEPTH
            )

        query_output = self.materialize_output(
            query_info,
            query_info["output"],
            objects_bucket,
            max_depth=MAX_OUTPUT_SELECTOR_DEPTH,
            minimal_materialization=minimal_materialization,
        )

        if query_inputs:
            query_inputs = f"({query_inputs})"

        payload = f"""
        query {{
            {name} {query_inputs}
            {query_output}
        }}
        """
        return prettify_graphql_payload(payload), self.used_objects

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _resolve_cursor_arg(self, query_info: dict) -> str | None:
        """Return the cursor argument name for this query."""
        pagination = query_info.get("pagination") or {}
        cursor_arg = pagination.get("cursor_arg")
        if cursor_arg:
            return cursor_arg
        # Fall back: scan input names for known cursor-arg patterns
        for arg_name in (query_info.get("inputs") or {}):
            if arg_name.lower() in _CURSOR_ARG_NAMES:
                return arg_name
        return None

    def _pick_fuzzed_cursor(self, objects_bucket: ObjectsBucket) -> str | None:
        """Find a captured cursor string in the bucket and return a mutated variant.

        Returns:
            A mutated cursor string, or ``None`` if no cursor was captured.
        """
        for key in _CURSOR_SCALAR_KEYS:
            scalar_entry = objects_bucket.scalars.get(key)
            if scalar_entry and scalar_entry.get("values"):
                original = random.choice(list(scalar_entry["values"]))
                if self.fuzz_mode == "idor":
                    variants = cursor_utils.mutate_for_idor(str(original))
                else:
                    variants = cursor_utils.mutate_for_injection(str(original))
                if variants:
                    return variants[0]
        return None

    def _materialize_inputs_with_cursor(
        self,
        query_info: dict,
        objects_bucket: ObjectsBucket,
        cursor_arg_name: str,
        fuzzed_cursor: str,
    ) -> str:
        """Materialise query inputs, substituting *fuzzed_cursor* for *cursor_arg_name*.

        All other inputs are materialised normally via the base class.
        """
        parts: list[str] = []
        for arg_name, arg_field in (query_info.get("inputs") or {}).items():
            if arg_name == cursor_arg_name:
                parts.append(f'{arg_name}: "{fuzzed_cursor}"')
            else:
                value = self.materialize_input_recursive(
                    query_info, arg_field, objects_bucket, arg_name, True, MAX_INPUT_DEPTH, 0
                )
                if value:
                    parts.append(f"{arg_name}: {value}")
        return ", ".join(parts)
