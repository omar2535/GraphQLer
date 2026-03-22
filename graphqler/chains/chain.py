"""Chain dataclass representing an ordered sequence of nodes to execute."""

from dataclasses import dataclass, field
from graphqler.graph.node import Node


@dataclass
class Chain:
    """An ordered list of nodes representing a root-to-leaf path (or a prefix thereof).

    **Regular chain** (``split_index is None``):
        All nodes run with the primary auth token.  The chain is fully self-sufficient —
        running it on an empty :class:`~graphqler.fuzzer.utils.objects_bucket.ObjectsBucket`
        will succeed because every prerequisite is created earlier in the same chain.

    **IDOR chain** (``split_index`` is an integer):
        The chain is split into two phases:

        - *Setup phase* — ``nodes[:split_index]`` run with the *primary* auth token.
          These nodes (typically CREATE mutations) produce objects and populate the bucket.
        - *Test phase*  — ``nodes[split_index:]`` run with the *secondary* (attacker) token.
          If any test node succeeds, an IDOR vulnerability is flagged.

        ``confidence`` and ``reason`` describe how the split was determined.

    Example
    -------
    IDOR: [createNote, getNote], split_index=1
      createNote  (primary token)  → bucket gets {noteId: "abc"}
      getNote(id="abc") (secondary token) → IDOR if data is returned
    """

    nodes: list[Node] = field(default_factory=list)
    name: str = ""
    split_index: int | None = None   # None = all nodes run with primary token
    confidence: float = 0.0          # classifier score when split_index is set
    reason: str = ""                 # human-readable explanation when split_index is set

    def __len__(self) -> int:
        return len(self.nodes)

    def __repr__(self) -> str:
        if self.split_index is not None:
            setup = " -> ".join(n.name for n in self.nodes[: self.split_index])
            test = " -> ".join(n.name for n in self.nodes[self.split_index :])
            return f"Chain([{setup}] || [{test}], confidence={self.confidence:.2f})"
        path = " -> ".join(n.name for n in self.nodes)
        return f"Chain([{path}])"

    def last_node(self) -> Node | None:
        """Returns the terminal (last) node in the chain, or None if the chain is empty."""
        if not self.nodes:
            return None
        return self.nodes[-1]

    def has_mutation_type(self, mutation_types: list[str]) -> bool:
        """Returns True if any node in the chain has a mutation_type in the given list."""
        return any(n.mutation_type in mutation_types for n in self.nodes)
