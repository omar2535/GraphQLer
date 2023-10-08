"""Param types: https://spec.graphql.org/June2018/#sec-Schema-Introspection
- Input name: The input name (different from the name)
- Kind
- Name
- ofType (NON_NULL AND LIST ONLY)
"""

from __future__ import annotations


class Input:
    def __init__(self, input_name: str, kind: str, name: str, ofType: Input = None):
        self.input_name = input_name
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
