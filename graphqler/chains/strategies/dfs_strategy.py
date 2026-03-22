"""DFS-based chain generation strategy."""

import networkx

from graphqler.chains.chain import Chain, ChainStep
from graphqler.chains.strategies.base_strategy import BaseChainStrategy
from graphqler.graph.node import Node


class DFSChainStrategy(BaseChainStrategy):
    """Generates chains via depth-first search from the starter nodes.

    For every node visited during DFS, the current prefix path is recorded as a :class:`Chain`.
    This means a path A -> B -> C produces three chains: [A], [A, B], [A, B, C].

    Cycles are avoided by tracking the nodes already present in the current path.

    Nodes whose ``mutation_type`` is in *filter_mutation_type* are excluded from chains;
    DFS stops at those nodes and does not recurse into their subtrees.
    """

    file_name = "regular.yml"

    def generate(self, graph: networkx.DiGraph, starter_nodes: list[Node],
                 source_chains: list[Chain] | None = None,
                 filter_mutation_type: list[str] | None = None) -> list[Chain]:
        """Run DFS from each starter node and collect all prefix chains.

        Args:
            graph (networkx.DiGraph): The dependency graph.
            starter_nodes (list[Node]): Nodes to begin DFS from.
            source_chains (list[Chain] | None): Accepted for interface compatibility; not used.
            filter_mutation_type (list[str] | None): Mutation types to exclude.
                Nodes whose ``mutation_type`` is in this list (and their entire subtrees)
                will be skipped. Pass ``None`` or ``[]`` to include all nodes.

        Returns:
            list[Chain]: All prefix chains discovered during DFS.
        """
        excluded = set(filter_mutation_type) if filter_mutation_type else set()
        chains: list[Chain] = []
        for start_node in starter_nodes:
            self._dfs(graph, start_node, [], chains, excluded)
        return chains

    def _dfs(self, graph: networkx.DiGraph, node: Node, current_path: list[Node],
             chains: list[Chain], excluded: set[str]) -> None:
        """Recursively performs DFS, appending a Chain for every prefix path.

        If a node's ``mutation_type`` is in *excluded*, it and its entire subtree are skipped.

        Args:
            graph (networkx.DiGraph): The dependency graph.
            node (Node): The current node being visited.
            current_path (list[Node]): Nodes visited so far on this path (not including *node*).
            chains (list[Chain]): Accumulator for discovered chains.
            excluded (set[str]): Mutation types to skip.
        """
        if node.mutation_type in excluded:
            return  # stop recursion — this node and its subtree are excluded

        new_path = current_path + [node]
        steps = [ChainStep(node=n) for n in new_path]
        chains.append(Chain(steps=steps))

        for neighbor in graph.successors(node):
            if neighbor not in new_path:  # avoid cycles
                self._dfs(graph, neighbor, new_path, chains, excluded)
