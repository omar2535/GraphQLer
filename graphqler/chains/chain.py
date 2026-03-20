"""Chain dataclass representing an ordered sequence of nodes to execute."""

from dataclasses import dataclass, field
from graphqler.graph.node import Node


@dataclass
class Chain:
    """An ordered list of nodes representing a root-to-leaf path (or a prefix thereof).

    Example: for a dependency path A -> B -> C, the following chains would be generated:
        Chain([A]), Chain([A, B]), Chain([A, B, C])

    Each chain is intended to be executed from start to finish with a fresh ObjectsBucket,
    ensuring all prerequisite nodes run before dependent ones within the same chain.
    """

    nodes: list[Node] = field(default_factory=list)
    name: str = ""

    def __len__(self) -> int:
        return len(self.nodes)

    def __repr__(self) -> str:
        path = " -> ".join(n.name for n in self.nodes)
        return f"Chain([{path}])"

    def last_node(self) -> Node | None:
        """Returns the terminal (last) node in the chain, or None if the chain is empty."""
        if not self.nodes:
            return None
        return self.nodes[-1]

    def has_mutation_type(self, mutation_types: list[str]) -> bool:
        """Returns True if any node in the chain has a mutation_type in the given list.

        Args:
            mutation_types (list[str]): Mutation types to check for (e.g. ["UPDATE", "DELETE"])

        Returns:
            bool: True if any node matches
        """
        return any(n.mutation_type in mutation_types for n in self.nodes)
