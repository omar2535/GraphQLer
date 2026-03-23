"""Chain dataclass representing an ordered sequence of nodes to execute."""

from dataclasses import dataclass, field
from graphqler.graph.node import Node


@dataclass
class ChainStep:
    """A single step within a chain, pairing a node with a runtime profile."""
    node: Node
    profile_name: str = "primary"  # Name of the runtime profile to use (e.g. "primary", "secondary")

    @property
    def context_name(self) -> str:
        """Backward-compatible alias for profile_name."""
        return self.profile_name

    def __repr__(self) -> str:
        return f"{self.node.name}[{self.profile_name}]"


@dataclass
class Chain:
    """An ordered list of steps representing a sequence of GraphQL operations.

    Each step identifies a node to execute and the runtime profile (auth token, etc.) to use.
    This allows for multi-user scenarios like IDOR testing within a single chain.

    Metadata like ``confidence`` and ``reason`` describe why this specific sequence
    was generated (e.g., as a candidate for IDOR testing).
    """

    steps: list[ChainStep] = field(default_factory=list)
    name: str = ""
    confidence: float = 1.0  # classifier score; 1.0 for statically-derived chains, heuristic score for IDOR candidates
    reason: str = ""         # human-readable explanation (if applicable)

    @property
    def nodes(self) -> list[Node]:
        """Backward-compatible access to the underlying nodes."""
        return [step.node for step in self.steps]

    def __len__(self) -> int:
        return len(self.steps)

    def __repr__(self) -> str:
        if not self.steps:
            return "Chain([])"
        path = " -> ".join(repr(step) for step in self.steps)
        return f"Chain([{path}])"

    def last_node(self) -> Node | None:
        """Returns the terminal (last) node in the chain, or None if the chain is empty."""
        if not self.steps:
            return None
        return self.steps[-1].node

    def has_mutation_type(self, mutation_types: list[str]) -> bool:
        """Returns True if any node in the chain has a mutation_type in the given list."""
        return any(step.node.mutation_type in mutation_types for step in self.steps)

    @property
    def is_multi_profile(self) -> bool:
        """Returns True if the chain contains steps with different profile names."""
        if not self.steps:
            return False
        first_profile = self.steps[0].profile_name
        return any(step.profile_name != first_profile for step in self.steps)

    @property
    def is_multi_context(self) -> bool:
        """Backward-compatible alias for is_multi_profile."""
        return self.is_multi_profile
