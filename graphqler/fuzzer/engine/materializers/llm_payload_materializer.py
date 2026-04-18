"""LLM Payload Materializer:
Uses an LLM to generate semantically-aware GraphQL payloads based on the
operation schema and the current objects bucket.

This is a pure LLM implementation — it always calls the LLM and raises on
failure.  It has no knowledge of fallback strategies; that is the
responsibility of ``GeneralPayloadMaterializer``.
"""

from __future__ import annotations

import json

from graphqler.utils.api import API
from graphqler.utils.logging_utils import Logger
from graphqler.utils.objects_bucket import ObjectsBucket

from .materializer import Materializer
from .utils.materialization_utils import prettify_graphql_payload


_SYSTEM_PROMPT = """\
You are a GraphQL API fuzzer assistant. Your job is to generate a valid \
GraphQL query or mutation for a given operation, using known objects from \
the objects bucket where appropriate to maximise coverage and semantic validity.

Respond with ONLY a JSON object in the following format:
{"payload": "<full GraphQL query or mutation string>"}

Rules:
- The payload MUST be syntactically valid GraphQL.
- You will be given an "output_schema" map. Each key is a type name and its \
  value is a dict of {field_name: kind} where kind is one of:
    "SCALAR"   — leaf value, select it directly (no braces).
    "ENUM"     — leaf value, select it directly (no braces).
    "OBJECT:TypeName" — nested object; you MUST follow it with a subselection \
  block { ... } using the fields listed under TypeName in output_schema.
    "LIST:TypeName"   — list of objects; you MUST follow it with a subselection \
  block { ... } using the fields listed under TypeName in output_schema.
    "LIST:SCALAR"     — list of scalars, select directly (no braces).
    "UNION:TypeName"  — union; use inline fragments (... on ConcreteType { id }).
- You MUST only select fields listed in output_schema — never invent field names.
- Every field annotated OBJECT:* or LIST:* (non-scalar list) MUST have a \
  subselection block. Omitting it causes a ValidationError.
- Be SELECTIVE: only choose fields that are semantically relevant to the \
  operation's purpose. Do NOT select every available field — prefer a small, \
  focused set (e.g. id, name, and one or two meaningful fields). Overly wide \
  selections are rejected by servers with query complexity limits.
- Prefer IDs and field values from the objects_bucket when they are available.
- For string inputs that have no bucket value, generate short realistic-looking \
  values that match the field name semantics.
- Include ALL required (NON_NULL) inputs.
- Do NOT include markdown fences or any text outside the JSON object.\
"""


def _summarise_bucket(objects_bucket: ObjectsBucket, max_items_per_type: int = 3) -> str:
    """Build a compact JSON summary of the objects bucket for the LLM prompt."""
    objects_summary = {
        obj_name: obj_list[:max_items_per_type]
        for obj_name, obj_list in objects_bucket.objects.items()
    }
    scalars_summary = {
        scalar_name: {"type": info["type"], "values": list(info["values"])[:max_items_per_type]}
        for scalar_name, info in objects_bucket.scalars.items()
    }
    return json.dumps({"objects": objects_summary, "scalars": scalars_summary}, default=str)


def _unwrap_field_kind(field: dict) -> tuple[str, str | None]:
    """Unwrap NON_NULL/LIST wrappers and return ``(annotation, inner_type_name)``.

    Returns a tuple of:
    - annotation: one of ``"SCALAR"``, ``"ENUM"``, ``"OBJECT:TypeName"``,
      ``"LIST:TypeName"``, ``"LIST:SCALAR"``, ``"UNION:TypeName"``
    - inner_type_name: the concrete type name if it is an OBJECT/LIST, else ``None``
    """
    kind = field.get("kind", "")
    type_name = field.get("type") or field.get("name")

    if kind == "NON_NULL":
        oftype = field.get("ofType")
        return _unwrap_field_kind(oftype) if oftype else ("SCALAR", None)

    if kind == "LIST":
        oftype = field.get("ofType")
        if not oftype:
            return ("LIST:SCALAR", None)
        inner_kind, inner_name = _unwrap_field_kind(oftype)
        if inner_kind == "SCALAR" or inner_kind == "ENUM":
            return ("LIST:SCALAR", None)
        # Inner is an object / union / interface
        inner_type = oftype.get("type") or oftype.get("name") or inner_name
        return (f"LIST:{inner_type}", inner_type)

    if kind == "OBJECT":
        return (f"OBJECT:{type_name}", type_name)

    if kind == "UNION":
        return (f"UNION:{type_name}", type_name)

    if kind == "INTERFACE":
        return (f"INTERFACE:{type_name}", type_name)

    # SCALAR, ENUM, or unknown
    return (kind if kind else "SCALAR", None)


def _resolve_output_types(output_field: dict, api_objects: dict, visited: set | None = None, max_depth: int = 3) -> dict:
    """Recursively resolve the output type tree into a ``{TypeName: {field_name: kind}}`` map.

    The kind annotation tells the LLM exactly which fields need a subselection
    block (``OBJECT:*`` and ``LIST:TypeName``) vs which are plain scalars.

    Types that fall outside ``max_depth`` are simply not added to the result.
    ``_prune_unresolvable_fields`` is then used to strip any field whose target
    type did not make it into the map, so the LLM never sees a field it cannot
    fully select.
    """
    if visited is None:
        visited = set()

    result: dict[str, dict[str, str]] = {}
    if not output_field or max_depth == 0:
        return result

    kind = output_field.get("kind", "")

    # Unwrap NON_NULL / LIST wrappers — the real type is in ofType
    if kind in ("NON_NULL", "LIST"):
        oftype = output_field.get("ofType")
        if oftype:
            result.update(_resolve_output_types(oftype, api_objects, visited, max_depth))
        return result

    type_name: str | None = output_field.get("type") or output_field.get("name")
    if not type_name or type_name in visited or kind != "OBJECT":
        return result

    visited.add(type_name)
    obj_info = api_objects.get(type_name)
    if not obj_info:
        return result

    field_annotations: dict[str, str] = {}
    for f in obj_info.get("fields", []):
        annotation, inner_name = _unwrap_field_kind(f)
        field_annotations[f["name"]] = annotation
        # Recurse into nested object fields
        if inner_name and inner_name not in visited:
            result.update(_resolve_output_types({"kind": "OBJECT", "type": inner_name, "name": inner_name}, api_objects, visited, max_depth - 1))

    result[type_name] = field_annotations
    return result


def _prune_unresolvable_fields(schema: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    """Remove fields from each type whose target type is not present in the schema.

    If a field is ``OBJECT:X`` or ``LIST:X`` (non-scalar list) but type ``X``
    is not a key in ``schema``, selecting that field in a GraphQL query would
    require a subselection the LLM cannot construct — so we omit it entirely.
    This prevents ``SubselectionRequired`` / ``FieldUndefined`` errors caused
    by the LLM guessing fields on unresolved types.
    """
    pruned: dict[str, dict[str, str]] = {}
    for type_name, fields in schema.items():
        pruned_fields: dict[str, str] = {}
        for field_name, annotation in fields.items():
            if ":" in annotation:
                prefix, target = annotation.split(":", 1)
                # LIST:SCALAR is fine — no subselection needed
                if target == "SCALAR" or target in schema:
                    pruned_fields[field_name] = annotation
                # else: target type unresolved — skip this field
            else:
                pruned_fields[field_name] = annotation
        pruned[type_name] = pruned_fields
    return pruned


def _get_root_type_name(output_field: dict) -> str | None:
    """Unwrap NON_NULL/LIST wrappers and return the root OBJECT type name."""
    kind = output_field.get("kind", "")
    if kind in ("NON_NULL", "LIST"):
        oftype = output_field.get("ofType")
        return _get_root_type_name(oftype) if oftype else None
    if kind == "OBJECT":
        return output_field.get("type") or output_field.get("name")
    return None


def _prune_selection_set(selections, type_name: str, output_schema: dict, indent: int = 2) -> str:
    """Recursively validate and rebuild a selection set as a string.

    Mirrors the regular materializer's Layer 2 guarantee:
    - Fields not present in ``output_schema`` are dropped.
    - ``OBJECT:*`` / ``LIST:TypeName`` fields without a subselection block are dropped.
    - ``OBJECT:*`` / ``LIST:TypeName`` fields whose subselection becomes empty after pruning
      are dropped (same as the ``is_valid_object_materialization`` check).
    - Non-field selections (inline fragments) are passed through unchanged.
    """
    from graphql import print_ast
    from graphql.language.ast import FieldNode

    type_fields = output_schema.get(type_name, {})
    pad = "  " * indent
    parts: list[str] = []

    for sel in selections:
        if not isinstance(sel, FieldNode):
            # Inline fragments / fragment spreads — pass through
            parts.append(pad + print_ast(sel))
            continue

        field_name = sel.name.value
        annotation = type_fields.get(field_name) if type_fields else None

        if annotation is None:
            if not type_fields:
                # Unknown type — can't validate, pass through
                parts.append(pad + print_ast(sel))
            # else: known type but field not listed — prune
            continue

        args_str = ""
        if sel.arguments:
            args_str = "(" + ", ".join(print_ast(a) for a in sel.arguments) + ")"

        if ":" in annotation:
            _, target = annotation.split(":", 1)
            if target == "SCALAR":
                parts.append(f"{pad}{field_name}{args_str}")
            else:
                # OBJECT or LIST of objects — must have a subselection
                if not sel.selection_set:
                    continue  # no subselection provided — prune
                inner = _prune_selection_set(sel.selection_set.selections, target, output_schema, indent + 1)
                if not inner.strip():
                    continue  # all children pruned — prune this field too
                parts.append(f"{pad}{field_name}{args_str} {{\n{inner}\n{pad}}}")
        else:
            # SCALAR or ENUM — leaf, no subselection
            parts.append(f"{pad}{field_name}{args_str}")

    return "\n".join(parts)


def _sanitize_payload(payload: str, name: str, graphql_type: str, operator_info: dict, output_schema: dict) -> str:
    """Post-generation validation: parse the LLM payload and prune any field that
    violates ``output_schema`` constraints (unknown field, missing subselection, etc.).

    This is the LLM-system equivalent of the regular materializer's Layer 2 check
    (``is_valid_object_materialization``).  Returns the pruned, prettified payload.
    Raises ``ValueError`` if the pruning leaves an empty selection set.
    """
    from graphql import parse, print_ast
    from graphql.language.ast import FieldNode, OperationDefinitionNode

    root_type = _get_root_type_name(operator_info.get("output", {}))
    if not root_type or root_type not in output_schema:
        return payload  # no schema info available — return as-is

    doc = parse(payload)
    op = doc.definitions[0]
    if not isinstance(op, OperationDefinitionNode):
        return payload

    # The operation's top-level selection contains the operation field (e.g. topLevelDocumentaryUnits).
    # Validate its *inner* selection set against root_type.
    for sel in op.selection_set.selections:
        if not isinstance(sel, FieldNode) or sel.name.value != name:
            continue
        if not sel.selection_set:
            return payload

        pruned_body = _prune_selection_set(sel.selection_set.selections, root_type, output_schema, indent=2)
        if not pruned_body.strip():
            raise ValueError(f"All output fields pruned from '{name}' after post-generation schema validation.")

        args_str = ""
        if sel.arguments:
            args_str = "(" + ", ".join(print_ast(a) for a in sel.arguments) + ")"

        op_keyword = graphql_type.lower()
        rebuilt = f"{op_keyword} {{\n  {name}{args_str} {{\n{pruned_body}\n  }}\n}}"
        return prettify_graphql_payload(rebuilt)

    return payload  # operation field not found — return as-is


def _format_operation_schema(name: str, graphql_type: str, operator_info: dict, output_schema: dict) -> str:
    """Serialise the relevant parts of the operator info for the LLM prompt.

    ``output_schema`` is the pre-computed, pruned field map — pass the result of
    ``_prune_unresolvable_fields(_resolve_output_types(...))`` directly so it is
    not recomputed here.
    """
    return json.dumps(
        {
            "name": name,
            "type": graphql_type,
            "inputs": operator_info.get("inputs", {}),
            "output": operator_info.get("output", {}),
            "output_schema": output_schema,
            "hardDependsOn": operator_info.get("hardDependsOn", {}),
            "softDependsOn": operator_info.get("softDependsOn", {}),
        },
        default=str,
    )


class LLMPayloadMaterializer(Materializer):
    """Payload materializer that exclusively uses an LLM to build payloads.

    Always calls the LLM and propagates any exception to the caller.
    Does not contain fallback or delegation logic.
    """

    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = True):
        super().__init__(api, fail_on_hard_dependency_not_met)
        self.logger = Logger().get_fuzzer_logger().getChild(__name__)

    def get_payload(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str) -> tuple[str, dict]:
        """Call the LLM to generate a payload and return ``(payload_string, used_objects)``.

        Raises on any failure (network error, bad JSON, invalid GraphQL, …).
        ``used_objects`` is always empty because the LLM constructs values
        inline rather than pulling tracked instances from the bucket.
        """
        from graphqler.utils.llm_utils import call_llm

        if graphql_type == "Query":
            operator_info = self.api.queries.get(name, {})
        elif graphql_type == "Mutation":
            operator_info = self.api.mutations.get(name, {})
        else:
            raise ValueError(f"Unsupported graphql_type for LLM materializer: {graphql_type!r}")

        output_schema = _prune_unresolvable_fields(_resolve_output_types(operator_info.get("output", {}), self.api.objects))

        user_prompt = (
            f"Generate a {graphql_type} payload for the following GraphQL operation.\n\n"
            f"Operation schema:\n{_format_operation_schema(name, graphql_type, operator_info, output_schema)}\n\n"
            f"Objects bucket (values already collected during this fuzzing run):\n{_summarise_bucket(objects_bucket)}"
        )

        response = call_llm(_SYSTEM_PROMPT, user_prompt)
        raw_payload: str = response.get("payload", "").strip()
        if not raw_payload:
            raise ValueError("LLM returned an empty payload field.")

        pretty_payload = prettify_graphql_payload(raw_payload)
        sanitized_payload = _sanitize_payload(pretty_payload, name, graphql_type, operator_info, output_schema)
        self.logger.info("[%s] LLM-generated payload:\n%s", name, sanitized_payload)
        return sanitized_payload, {}

