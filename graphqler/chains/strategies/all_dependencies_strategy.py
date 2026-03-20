"""AllDependencies chain generation strategy."""

from typing import cast

import networkx

from graphqler.chains.chain import Chain
from graphqler.chains.strategies.base_strategy import BaseChainStrategy
from graphqler.graph.node import Node

# Lower value = earlier in chain within a strongly connected component.
# Mirrors the 3-pass logic in ChainGenerator:
#   CREATE runs first (produces objects), then Objects are populated,
#   then Queries read them, then UPDATE modifies them, DELETE/UNKNOWN run last.
_NODE_PRIORITY: dict[str, int] = {
    "CREATE": 0,
    "Object": 1,   # keyed on graphql_type for non-mutation nodes
    "Query": 2,
    "UPDATE": 3,
    "DELETE": 4,
    "UNKNOWN": 5,
}


class AllDependenciesChainStrategy(BaseChainStrategy):
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

    The *starter_nodes* parameter is accepted for interface compatibility but is
    ignored — every non-filtered node in the graph gets its own chain.
    """

    def generate(self, graph: networkx.DiGraph, starter_nodes: list[Node],
                 filter_mutation_type: list[str] | None = None) -> list[Chain]:
        """Generate one self-sufficient chain per non-filtered node.

        Args:
            graph (networkx.DiGraph): The dependency graph.
            starter_nodes (list[Node]): Accepted for interface compatibility; not used.
            filter_mutation_type (list[str] | None): Mutation types to exclude.
                Nodes with a ``mutation_type`` in this list are skipped entirely;
                they are also removed from ancestor sets of other chains.
                Pass ``None`` or ``[]`` to include all nodes.

        Returns:
            list[Chain]: One chain per non-filtered node in stable order.
        """
        excluded = set(filter_mutation_type) if filter_mutation_type else set()
        chains: list[Chain] = []

        for node in self._safe_topo_sort(graph):
            if node.mutation_type in excluded:
                continue

            # All transitive predecessors, excluding filtered nodes
            ancestors = cast(set[Node], networkx.ancestors(graph, node))
            valid_ancestors: set[Node] = {
                a for a in ancestors
                if a.mutation_type not in excluded
            }

            chain_node_set = valid_ancestors | {node}
            subgraph = cast(networkx.DiGraph, graph.subgraph(chain_node_set))
            sorted_nodes = self._safe_topo_sort(subgraph)

            chains.append(Chain(nodes=sorted_nodes))

        return chains

    def _safe_topo_sort(self, graph: networkx.DiGraph) -> list[Node]:
        """Topological sort that handles cycles via SCC condensation.

        Uses ``networkx.condensation()`` to collapse cycles into single nodes
        (always a DAG), topological-sorts the condensation, then expands each
        SCC back to its member nodes sorted by ``graphql_type`` priority
        (Mutation → Object → Query) so that creators run before their products.

        Args:
            graph (networkx.DiGraph): Any directed graph, cyclic or acyclic.

        Returns:
            list[Node]: Nodes in a valid dependency order.
        """
        condensation = networkx.condensation(graph)
        result: list[Node] = []
        for cond_node in networkx.topological_sort(condensation):
            members: set[Node] = condensation.nodes[cond_node]["members"]
            ordered = sorted(members, key=self._node_sort_key)
            result.extend(ordered)
        return result

    @staticmethod
    def _node_sort_key(node: Node) -> tuple[int, str]:
        """Return a sort key that respects dependency order within an SCC.

        For Mutation nodes the ``mutation_type`` (CREATE/UPDATE/DELETE/UNKNOWN) is used.
        For all other nodes the ``graphql_type`` (Object/Query) is used.
        """
        if node.graphql_type == "Mutation":
            key = _NODE_PRIORITY.get(node.mutation_type or "UNKNOWN", 5)
        else:
            key = _NODE_PRIORITY.get(node.graphql_type, 1)
        return (key, node.name)
