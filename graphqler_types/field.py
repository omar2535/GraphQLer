"""Field types: https://spec.graphql.org/June2018/#sec-Schema-Introspection
- Input name: The input name (different from the name)
- Kind
- Name
- ofType (NON_NULL AND LIST ONLY)
"""

from __future__ import annotations


class Field:
    def __init__(self, kind: str, name: str, type: str, oftype: Field = None):
        self.kind = kind
        self.name = name
        self.type = type
        self.oftype = oftype

    def is_required(self) -> bool:
        """Whether this field is NOT_NULL or not

        Returns:
            bool: True if this is a NON_NULL parameter, False otherwise
        """
        return self.kind == "NON_NULL"

    def has_oftype(self) -> bool:
        """Whether this field has oftypes or not

        Returns:
            bool: True if this input has an oftype, False otherwise
        """
        return self.oftype is not None
