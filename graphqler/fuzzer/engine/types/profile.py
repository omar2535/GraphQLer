"""RuntimeProfile: defines the execution context for a GraphQL operation."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeProfile:
    """A profile defining the runtime environment for executing a GraphQL operation.

    Includes authentication tokens, custom headers, and other arbitrary variables.
    """
    name: str
    auth_token: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)

    def get_headers(self) -> dict[str, str]:
        """Return headers for this profile, including Authorization if present."""
        h = self.headers.copy()
        if self.auth_token:
            # Handle Bearer prefix if missing and not empty
            token = self.auth_token
            if token and not token.startswith(("Bearer ", "Basic ")):
                token = f"Bearer {token}"
            h["Authorization"] = token
        return h
