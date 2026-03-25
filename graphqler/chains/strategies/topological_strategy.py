"""Topological chain generation strategy."""

from typing import cast

import networkx

from graphqler import config
from graphqler.chains.chain import Chain, ChainStep
from graphqler.chains.strategies.base_strategy import BaseChainStrategy
from graphqler.graph.node import Node

# Lower value = earlier in chain within a strongly connected component.
# CREATE runs first (produces objects), then Objects are populated,
# then Queries read them, then UPDATE modifies them, DELETE/UNKNOWN run last.
_NODE_PRIORITY: dict[str, int] = {
    "CREATE": 0,
    "Object": 1,
    "Query": 2,
    "UPDATE": 3,
    "DELETE": 4,
    "UNKNOWN": 5,
}

_ALL_MUTATION_TYPES = ["CREATE", "UPDATE", "DELETE", "UNKNOWN"]


class TopologicalChainStrategy(BaseChainStrategy):
    """Generates one self-sufficient chain per node by including all transitive dependencies.

    For every node N in topological order:

    1. Compute ``networkx.ancestors(graph, N)`` — all transitive predecessors.
    2. Remove ancestors whose ``mutation_type`` is in *filter_mutation_type*.
    3. Build a subgraph view from ``valid_ancestors U {N}`` — the original edges
       between those nodes are preserved automatically by NetworkX.
    4. Topological-sort the subgraph using SCC condensation (handles cycles gracefully).

    **Cycle handling:** Real-world GraphQL APIs produce cycles in the dependency graph
    (e.g. a ``restaurant`` query both *returns* and *requires* a ``Restaurant`` object).
    Plain ``topological_sort`` gives invalid orderings on cyclic graphs.  This strategy
    uses ``networkx.condensation()`` to collapse each strongly-connected component (SCC)
    into a single node, topological-sorts the resulting DAG, then expands each SCC back
    to its member nodes sorted by type priority (Mutation → Object → Query).  This
    ensures that CREATE mutations in the same SCC run before the objects they produce.

    The resulting chain is **fully self-sufficient**: running it on a truly empty
    :class:`~graphqler.fuzzer.utils.objects_bucket.ObjectsBucket` will succeed
    because every prerequisite is created earlier in the same chain.

    :meth:`generate` runs the standard 3-pass filtering strategy:

    * Pass 1 — CREATE + QUERY only (filter UPDATE, DELETE, UNKNOWN)
    * Pass 2 — CREATE + QUERY + UPDATE (filter DELETE, UNKNOWN)
    * Pass 3 — all nodes

    When ``config.DISABLE_MUTATIONS`` is ``True``, only a single query-only pass
    is performed (all mutation types filtered out).
    """

    file_name = "regular.yml"

    def generate(self, graph: networkx.DiGraph | None, starter_nodes: list[Node], source_chains: list[Chain] | None = None, filter_mutation_type: list[str] | None = None) -> list[Chain]:
        """Run the standard 3-pass filtering strategy and return all chains combined.

        Args:
            graph (networkx.DiGraph | None): The dependency graph, or ``None`` if unavailable.
            starter_nodes (list[Node]): Accepted for interface compatibility; not used.
            source_chains (list[Chain] | None): Accepted for interface compatibility; not used.
            filter_mutation_type (list[str] | None): Mutation types to exclude from all passes.

        Returns:
            list[Chain]: Concatenation of all passes in order.
        """
        if graph is None:
            return []
        def merge(p):
            return list(set(p) | set(filter_mutation_type or []))

        if config.DISABLE_MUTATIONS:
            return self._generate_with_filter(graph, starter_nodes, source_chains, filter_mutation_type=merge(_ALL_MUTATION_TYPES))

        pass1 = self._generate_with_filter(graph, starter_nodes, source_chains, filter_mutation_type=merge(["UPDATE", "DELETE", "UNKNOWN"]))
        pass2 = self._generate_with_filter(graph, starter_nodes, source_chains, filter_mutation_type=merge(["DELETE", "UNKNOWN"]))
        pass3 = self._generate_with_filter(graph, starter_nodes, source_chains, filter_mutation_type=merge([]))
        return pass1 + pass2 + pass3

    def _generate_with_filter(self, graph: networkx.DiGraph, starter_nodes: list[Node],
                               source_chains: list[Chain] | None = None,
                               filter_mutation_type: list[str] | None = None) -> list[Chain]:
        """Generate one self-sufficient chain per non-filtered node.

        Args:
            graph (networkx.DiGraph): The dependency graph.
            starter_nodes (list[Node]): Accepted for interface compatibility; not used.
            source_chains (list[Chain] | None): Accepted for interface compatibility; not used.
            filter_mutation_type (list[str] | None): Mutation types to exclude.

        Returns:
            list[Chain]: One chain per non-filtered node in stable order.
        """
        excluded = set(filter_mutation_type) if filter_mutation_type else set()
        chains: list[Chain] = []

        for node in self._safe_topo_sort(graph):
            if node.mutation_type in excluded:
                continue

            ancestors = cast(set[Node], networkx.ancestors(graph, node))
            valid_ancestors: set[Node] = {
                a for a in ancestors
                if a.mutation_type not in excluded
            }

            chain_node_set = valid_ancestors | {node}
            subgraph = cast(networkx.DiGraph, graph.subgraph(chain_node_set))
            sorted_nodes = self._safe_topo_sort(subgraph)

            steps = [ChainStep(node=n) for n in sorted_nodes]
            chains.append(Chain(steps=steps))

        return chains

    def _safe_topo_sort(self, graph: networkx.DiGraph) -> list[Node]:
        """Topological sort that handles cycles via SCC condensation."""
        condensation = networkx.condensation(graph)
        result: list[Node] = []
        for cond_node in networkx.topological_sort(condensation):
            members: set[Node] = condensation.nodes[cond_node]["members"]
            ordered = sorted(members, key=self._node_sort_key)
            result.extend(ordered)
        return result

    @staticmethod
    def _node_sort_key(node: Node) -> tuple[int, str]:
        """Return a sort key that respects dependency order within an SCC."""
        if node.graphql_type == "Mutation":
            key = _NODE_PRIORITY.get(node.mutation_type or "UNKNOWN", 5)
        else:
            key = _NODE_PRIORITY.get(node.graphql_type, 1)
        return (key, node.name)
