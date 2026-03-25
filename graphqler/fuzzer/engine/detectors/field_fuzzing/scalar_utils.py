"""Shared scalar-type resolution helpers for field-fuzzing detectors."""


def _resolve_scalar_type(field_info: dict | None) -> str | None:
    """Walk NON_NULL / LIST wrappers until a SCALAR is reached; return its type name."""
    if field_info is None:
        return None
    if field_info.get("kind") == "SCALAR":
        return field_info.get("type")
    return _resolve_scalar_type(field_info.get("ofType"))
