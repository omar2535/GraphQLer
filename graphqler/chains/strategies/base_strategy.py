"""Abstract base class for chain generation strategies."""

from abc import ABC, abstractmethod

import networkx

from graphqler.chains.chain import Chain
from graphqler.graph.node import Node


class BaseChainStrategy(ABC):
    """Abstract base class for dependency-chain generation strategies.

    Subclasses implement :meth:`generate` to produce a list of :class:`Chain` objects
    from the dependency graph and a set of starter nodes.
    """

    @abstractmethod
    def generate(self,
                 graph: networkx.DiGraph,
                 starter_nodes: list[Node],
                 filter_mutation_type: list[str] | None = None) -> list[Chain]:
        """Generate chains from the dependency graph.

        Args:
            graph (networkx.DiGraph): The compiled dependency graph.
            starter_nodes (list[Node]): Root nodes (nodes with no, or minimal, in-degree).
            filter_mutation_type (list[str] | None): Mutation types whose nodes should be
                excluded from generated chains (and whose subtrees are not traversed).
                Pass an empty list or ``None`` to include all nodes. Defaults to ``None``.

        Returns:
            list[Chain]: The generated chains.
        """
        ...
