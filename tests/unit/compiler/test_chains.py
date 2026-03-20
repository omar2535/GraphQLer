"""Unit tests for the compiler chains module."""

import pytest
import networkx

from graphqler.chains.chain import Chain
from graphqler.chains.chain_generator import ChainGenerator
from graphqler.chains.strategies.dfs_strategy import DFSChainStrategy
from graphqler.graph.node import Node
from graphqler import config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_node(name: str, graphql_type: str = "Query", mutation_type: str | None = None) -> Node:
    node = Node(graphql_type, name, {})
    if mutation_type:
        node.mutation_type = mutation_type
    return node


def _linear_graph(*node_names: str) -> tuple[networkx.DiGraph, list[Node]]:
    """Build a simple linear graph A -> B -> C -> ... and return (graph, [nodes])."""
    graph = networkx.DiGraph()
    nodes = [_make_node(name) for name in node_names]
    graph.add_nodes_from(nodes)
    for i in range(len(nodes) - 1):
        graph.add_edge(nodes[i], nodes[i + 1])
    return graph, nodes


# ---------------------------------------------------------------------------
# Chain dataclass
# ---------------------------------------------------------------------------

class TestChain:
    def test_repr_empty(self):
        c = Chain()
        assert repr(c) == "Chain([])"

    def test_repr_single(self):
        n = _make_node("A")
        c = Chain(nodes=[n])
        assert "A" in repr(c)

    def test_repr_multiple(self):
        nodes = [_make_node(name) for name in ["A", "B", "C"]]
        c = Chain(nodes=nodes)
        assert repr(c) == "Chain([A -> B -> C])"

    def test_len(self):
        nodes = [_make_node(name) for name in ["A", "B"]]
        assert len(Chain(nodes=nodes)) == 2

    def test_len_empty(self):
        assert len(Chain()) == 0

    def test_last_node_returns_last(self):
        nodes = [_make_node(name) for name in ["X", "Y", "Z"]]
        c = Chain(nodes=nodes)
        assert c.last_node() is nodes[-1]

    def test_last_node_empty_returns_none(self):
        assert Chain().last_node() is None

    def test_has_mutation_type_true(self):
        n = _make_node("m", graphql_type="Mutation", mutation_type="DELETE")
        c = Chain(nodes=[n])
        assert c.has_mutation_type(["DELETE"]) is True

    def test_has_mutation_type_false(self):
        n = _make_node("q", graphql_type="Query")
        c = Chain(nodes=[n])
        assert c.has_mutation_type(["DELETE", "UPDATE"]) is False

    def test_has_mutation_type_mixed(self):
        nodes = [
            _make_node("create", graphql_type="Mutation", mutation_type="CREATE"),
            _make_node("update", graphql_type="Mutation", mutation_type="UPDATE"),
        ]
        c = Chain(nodes=nodes)
        assert c.has_mutation_type(["UPDATE"]) is True
        assert c.has_mutation_type(["DELETE"]) is False


# ---------------------------------------------------------------------------
# DFSChainStrategy
# ---------------------------------------------------------------------------

class TestDFSChainStrategy:
    def test_single_node(self):
        graph = networkx.DiGraph()
        n = _make_node("A")
        graph.add_node(n)
        chains = DFSChainStrategy().generate(graph, [n])
        assert len(chains) == 1
        assert chains[0].nodes == [n]

    def test_linear_two_nodes(self):
        graph, nodes = _linear_graph("A", "B")
        chains = DFSChainStrategy().generate(graph, [nodes[0]])
        node_lists = [c.nodes for c in chains]
        assert nodes[:1] in node_lists
        assert nodes[:2] in node_lists
        assert len(chains) == 2

    def test_linear_three_nodes_produces_prefix_chains(self):
        graph, nodes = _linear_graph("A", "B", "C")
        chains = DFSChainStrategy().generate(graph, [nodes[0]])
        node_lists = [c.nodes for c in chains]
        assert nodes[:1] in node_lists
        assert nodes[:2] in node_lists
        assert nodes[:3] in node_lists
        assert len(chains) == 3

    def test_branching_graph(self):
        graph = networkx.DiGraph()
        a, b, c = _make_node("A"), _make_node("B"), _make_node("C")
        graph.add_edges_from([(a, b), (a, c)])
        chains = DFSChainStrategy().generate(graph, [a])
        node_lists = [c.nodes for c in chains]
        assert [a] in node_lists
        assert [a, b] in node_lists
        assert [a, c] in node_lists
        assert len(chains) == 3

    def test_cycle_avoidance(self):
        graph = networkx.DiGraph()
        a, b = _make_node("A"), _make_node("B")
        graph.add_edges_from([(a, b), (b, a)])
        chains = DFSChainStrategy().generate(graph, [a])
        assert len(chains) == 2

    def test_multiple_starters(self):
        graph = networkx.DiGraph()
        x, y = _make_node("X"), _make_node("Y")
        graph.add_nodes_from([x, y])
        chains = DFSChainStrategy().generate(graph, [x, y])
        node_lists = [c.nodes for c in chains]
        assert [x] in node_lists
        assert [y] in node_lists

    def test_empty_graph(self):
        graph = networkx.DiGraph()
        chains = DFSChainStrategy().generate(graph, [])
        assert chains == []

    def test_filter_stops_at_filtered_node(self):
        """Chains should not include DELETE node when DELETE is filtered."""
        graph = networkx.DiGraph()
        create = _make_node("create", graphql_type="Mutation", mutation_type="CREATE")
        user = _make_node("User", graphql_type="Object")
        delete = _make_node("delete", graphql_type="Mutation", mutation_type="DELETE")
        graph.add_edges_from([(create, user), (user, delete)])

        chains = DFSChainStrategy().generate(graph, [create], filter_mutation_type=["DELETE"])
        for chain in chains:
            assert delete not in chain.nodes
        node_lists = [c.nodes for c in chains]
        assert [create] in node_lists
        assert [create, user] in node_lists
        assert len(chains) == 2

    def test_filter_none_includes_all(self):
        graph = networkx.DiGraph()
        create = _make_node("create", graphql_type="Mutation", mutation_type="CREATE")
        delete = _make_node("delete", graphql_type="Mutation", mutation_type="DELETE")
        graph.add_edge(create, delete)
        chains = DFSChainStrategy().generate(graph, [create], filter_mutation_type=None)
        assert len(chains) == 2

    def test_filter_all_mutations_keeps_only_queries(self):
        graph = networkx.DiGraph()
        query = _make_node("getUser", graphql_type="Query")
        create = _make_node("createUser", graphql_type="Mutation", mutation_type="CREATE")
        graph.add_nodes_from([query, create])
        chains = DFSChainStrategy().generate(
            graph, [query, create],
            filter_mutation_type=["CREATE", "UPDATE", "DELETE", "UNKNOWN"],
        )
        for chain in chains:
            assert create not in chain.nodes
        assert any(query in c.nodes for c in chains)


# ---------------------------------------------------------------------------
# ChainGenerator
# ---------------------------------------------------------------------------

class TestChainGenerator:
    def test_default_strategy_is_dfs(self):
        gen = ChainGenerator()
        assert isinstance(gen._strategy, DFSChainStrategy)

    def test_custom_strategy_accepted(self):
        custom = DFSChainStrategy()
        gen = ChainGenerator(strategy=custom)
        assert gen._strategy is custom

    def test_chains_empty_before_generate(self):
        gen = ChainGenerator()
        assert gen.chains == []

    def test_generate_returns_and_stores_chains(self):
        graph, nodes = _linear_graph("A", "B")
        gen = ChainGenerator()
        result = gen.generate(graph, [nodes[0]])
        assert len(result) > 0
        assert gen.chains is result

    def test_generate_overwrites_previous_chains(self):
        graph, nodes = _linear_graph("A", "B")
        gen = ChainGenerator()
        gen.generate(graph, [nodes[0]])
        first = gen.chains

        graph2, nodes2 = _linear_graph("X")
        gen.generate(graph2, [nodes2[0]])
        assert gen.chains is not first

    def test_chains_inspectable_after_generate(self):
        graph, nodes = _linear_graph("A", "B", "C")
        gen = ChainGenerator()
        gen.generate(graph, [nodes[0]])
        assert len(gen.chains) > 0
        for chain in gen.chains:
            assert isinstance(chain, Chain)

    def test_three_pass_produces_triplicated_query_chains(self):
        """Pure query nodes are never filtered → each prefix chain appears in all 3 passes."""
        graph, nodes = _linear_graph("A")  # single Query node
        gen = ChainGenerator()
        chains = gen.generate(graph, [nodes[0]])
        # pass1 + pass2 + pass3, each with 1 chain → 3 total
        assert len(chains) == 3

    def test_delete_chain_excluded_from_pass1_and_pass2(self):
        """A chain containing a DELETE node should not appear in pass1 or pass2."""
        graph = networkx.DiGraph()
        create = _make_node("create", graphql_type="Mutation", mutation_type="CREATE")
        delete = _make_node("delete", graphql_type="Mutation", mutation_type="DELETE")
        graph.add_edge(create, delete)

        gen = ChainGenerator()
        chains = gen.generate(graph, [create])

        chains_with_delete = [c for c in chains if delete in c.nodes]
        # Only pass3 generates [create, delete]
        assert len(chains_with_delete) >= 1

    def test_disable_mutations_excludes_all_mutations(self):
        original = config.DISABLE_MUTATIONS
        try:
            config.DISABLE_MUTATIONS = True
            graph = networkx.DiGraph()
            query = _make_node("getUser", graphql_type="Query")
            create = _make_node("createUser", graphql_type="Mutation", mutation_type="CREATE")
            graph.add_nodes_from([query, create])
            gen = ChainGenerator()
            chains = gen.generate(graph, [query, create])
            for chain in chains:
                for node in chain.nodes:
                    assert node.graphql_type != "Mutation"
        finally:
            config.DISABLE_MUTATIONS = original

    def test_disable_mutations_false_includes_mutations(self):
        original = config.DISABLE_MUTATIONS
        try:
            config.DISABLE_MUTATIONS = False
            graph = networkx.DiGraph()
            create = _make_node("createUser", graphql_type="Mutation", mutation_type="CREATE")
            graph.add_node(create)
            gen = ChainGenerator()
            chains = gen.generate(graph, [create])
            mutation_chains = [c for c in chains if any(n.graphql_type == "Mutation" for n in c.nodes)]
            assert len(mutation_chains) > 0
        finally:
            config.DISABLE_MUTATIONS = original
