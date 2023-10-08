"""Param types: https://spec.graphql.org/June2018/#sec-Schema-Introspection
- Kind
- Name
- ofType (NON_NULL AND LIST ONLY)
"""

from __future__ import annotations


class Output:
    def __init__(self, kind: str, name: str, ofType: Output = None):
        self.kind = kind
        self.name = name
        self.ofType = ofType

    def is_required(self) -> bool:
        """Whether this parameter is NOT_NULL or not

        Returns:
            bool: True if this is a NON_NULL parameter, False otherwise
        """
        return self.kind == "NON_NULL"

    def has_oftype(self) -> bool:
        """Whether this input has oftypes or not

        Returns:
            bool: True if this input has an oftype, False otherwise
        """
        return self.ofType is not None
