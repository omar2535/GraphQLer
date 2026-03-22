"""Unit tests for the compiler chains module."""

import networkx

from graphqler.chains.chain import Chain, ChainStep
from graphqler.chains.chain_generator import ChainGenerator
from graphqler.chains.strategies.dfs_strategy import DFSChainStrategy
from graphqler.chains.strategies.topological_strategy import TopologicalChainStrategy
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


def _names(chain: "Chain") -> list:
    """Return the list of node names in a chain."""
    return [n.name for n in chain.nodes]


# ---------------------------------------------------------------------------
# Chain dataclass
# ---------------------------------------------------------------------------

class TestChain:
    def test_repr_empty(self):
        c = Chain()
        assert repr(c) == "Chain([])"

    def test_repr_single(self):
        n = _make_node("A")
        c = Chain(steps=[ChainStep(node=n)])
        assert "A[primary]" in repr(c)

    def test_repr_multiple(self):
        nodes = [_make_node(name) for name in ["A", "B", "C"]]
        c = Chain(steps=[ChainStep(node=n) for n in nodes])
        assert "A[primary] -> B[primary] -> C[primary]" in repr(c)

    def test_len(self):
        nodes = [_make_node(name) for name in ["A", "B"]]
        assert len(Chain(steps=[ChainStep(node=n) for n in nodes])) == 2

    def test_len_empty(self):
        assert len(Chain()) == 0

    def test_last_node_returns_last(self):
        nodes = [_make_node(name) for name in ["X", "Y", "Z"]]
        c = Chain(steps=[ChainStep(node=n) for n in nodes])
        assert c.last_node() is nodes[-1]

    def test_last_node_empty_returns_none(self):
        assert Chain().last_node() is None

    def test_has_mutation_type_true(self):
        n = _make_node("m", graphql_type="Mutation", mutation_type="DELETE")
        c = Chain(steps=[ChainStep(node=n)])
        assert c.has_mutation_type(["DELETE"]) is True

    def test_has_mutation_type_false(self):
        n = _make_node("q", graphql_type="Query")
        c = Chain(steps=[ChainStep(node=n)])
        assert c.has_mutation_type(["DELETE", "UPDATE"]) is False

    def test_is_multi_profile_false(self):
        n = _make_node("q", graphql_type="Query")
        c = Chain(steps=[ChainStep(node=n, profile_name="primary")])
        assert c.is_multi_profile is False

    def test_is_multi_profile_true(self):
        n1 = _make_node("q1", graphql_type="Query")
        n2 = _make_node("q2", graphql_type="Query")
        c = Chain(steps=[
            ChainStep(node=n1, profile_name="primary"),
            ChainStep(node=n2, profile_name="secondary")
        ])
        assert c.is_multi_profile is True


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

    def test_linear_path(self):
        graph, nodes = _linear_graph("A", "B", "C")
        chains = DFSChainStrategy().generate(graph, [nodes[0]])
        # Should produce prefixes: [A], [A, B], [A, B, C]
        assert len(chains) == 3
        assert _names(chains[0]) == ["A"]
        assert _names(chains[1]) == ["A", "B"]
        assert _names(chains[2]) == ["A", "B", "C"]

    def test_branching_path(self):
        graph, nodes = _linear_graph("A", "B")
        c = _make_node("C")
        graph.add_edge(nodes[0], c)  # A -> B, A -> C
        chains = DFSChainStrategy().generate(graph, [nodes[0]])
        # [A], [A, B], [A, C]
        assert len(chains) == 3
        names = [_names(c) for c in chains]
        assert ["A"] in names
        assert ["A", "B"] in names
        assert ["A", "C"] in names

    def test_cycle_avoidance(self):
        a, b = _make_node("A"), _make_node("B")
        graph = networkx.DiGraph()
        graph.add_edge(a, b)
        graph.add_edge(b, a)
        chains = DFSChainStrategy().generate(graph, [a])
        # [A], [A, B] -- DFS stops at B because A is already in path
        assert len(chains) == 2
        assert _names(chains[0]) == ["A"]
        assert _names(chains[1]) == ["A", "B"]

    def test_multiple_starter_nodes(self):
        graph = networkx.DiGraph()
        x, y = _make_node("X"), _make_node("Y")
        graph.add_nodes_from([x, y])
        chains = DFSChainStrategy().generate(graph, [x, y])
        assert len(chains) == 2
        assert _names(chains[0]) == ["X"]
        assert _names(chains[1]) == ["Y"]

    def test_no_starter_nodes(self):
        graph, nodes = _linear_graph("A", "B")
        chains = DFSChainStrategy().generate(graph, [])
        assert len(chains) == 0

    def test_filter_mutation_type(self):
        graph = networkx.DiGraph()
        create = _make_node("create", graphql_type="Mutation", mutation_type="CREATE")
        delete = _make_node("delete", graphql_type="Mutation", mutation_type="DELETE")
        graph.add_edge(create, delete)

        # Filtering DELETE should stop DFS at 'create'
        chains = DFSChainStrategy().generate(graph, [create], filter_mutation_type=["DELETE"])
        assert len(chains) == 1
        assert _names(chains[0]) == ["create"]

    def test_filter_mutation_type_none_includes_all(self):
        graph = networkx.DiGraph()
        create = _make_node("create", graphql_type="Mutation", mutation_type="CREATE")
        graph.add_node(create)
        chains = DFSChainStrategy().generate(graph, [create], filter_mutation_type=None)
        assert len(chains) == 1


# ---------------------------------------------------------------------------
# ChainGenerator
# ---------------------------------------------------------------------------

class TestChainGenerator:
    def test_chains_empty_before_generate(self):
        gen = ChainGenerator()
        assert gen.chains == []

    def test_generate_with_strategy_returns_and_accumulates_chains(self):
        graph, nodes = _linear_graph("A", "B")
        gen = ChainGenerator()
        strategy = TopologicalChainStrategy()
        # Use a dummy source_chains list to match new signature
        result = gen.generate_with_strategy(strategy, graph, [nodes[0]], [])
        assert len(result) > 0
        assert all(c in gen.chains for c in result)

    def test_generate_with_multiple_strategies_accumulates_chains(self):
        graph, nodes = _linear_graph("A", "B")
        gen = ChainGenerator()

        topo_strategy = TopologicalChainStrategy()
        topo_chains = gen.generate_with_strategy(topo_strategy, graph, [nodes[0]], [])

        dfs_strategy = DFSChainStrategy()
        dfs_chains = gen.generate_with_strategy(dfs_strategy, graph, [nodes[0]], [])

        assert len(gen.chains) == len(topo_chains) + len(dfs_chains)
        assert all(c in gen.chains for c in topo_chains)
        assert all(c in gen.chains for c in dfs_chains)

    def test_chains_inspectable_after_generate(self):
        graph, nodes = _linear_graph("A", "B", "C")
        gen = ChainGenerator()
        gen.generate_with_strategy(TopologicalChainStrategy(), graph, [nodes[0]], [])
        assert len(gen.chains) > 0
        for chain in gen.chains:
            assert isinstance(chain, Chain)


# ---------------------------------------------------------------------------
# TopologicalChainStrategy
# ---------------------------------------------------------------------------

class TestTopologicalChainStrategy:
    def _strategy(self) -> TopologicalChainStrategy:
        return TopologicalChainStrategy()

    def test_single_node(self):
        graph, nodes = _linear_graph("A")
        chains = self._strategy().generate(graph, [])
        # pass1 + pass2 + pass3 = 3 chains if it's a Query/Object
        assert len(chains) == 3
        assert _names(chains[0]) == ["A"]

    def test_linear_chain_produces_one_chain_per_node(self):
        """A -> B -> C -> D: each node gets its own self-sufficient chain."""
        graph, nodes = _linear_graph("A", "B", "C", "D")
        chains = self._strategy().generate(graph, [])
        # 4 nodes * 3 passes = 12 total
        assert len(chains) == 12

        # Each node should be the last node in at least one chain (in each pass)
        all_lasts = [_names(c)[-1] for c in chains]
        for name in "ABCD":
            assert all_lasts.count(name) == 3

    def test_diamond_multi_parent(self):
        """B and C both depend on A; D depends on both B and C."""
        A, B, C, D = [_make_node(n) for n in "ABCD"]
        graph = networkx.DiGraph()
        graph.add_edge(A, B)
        graph.add_edge(A, C)
        graph.add_edge(B, D)
        graph.add_edge(C, D)

        chains = self._strategy().generate(graph, [])
        # 4 nodes * 3 passes = 12
        assert len(chains) == 12

        # In pass 3 (the last 4 chains), check D's chain
        d_chain = _names(chains[-1])
        assert set(d_chain) == {"A", "B", "C", "D"}
        assert d_chain[-1] == "D"
        assert d_chain.index("A") < d_chain.index("B")
        assert d_chain.index("A") < d_chain.index("C")
        assert d_chain.index("B") < d_chain.index("D")
        assert d_chain.index("C") < d_chain.index("D")

    def test_filter_excludes_nodes(self):
        """A filtered node should produce no chain."""
        create = _make_node("create", graphql_type="Mutation", mutation_type="CREATE")
        obj = _make_node("Obj", graphql_type="Object")
        delete = _make_node("delete", graphql_type="Mutation", mutation_type="DELETE")
        graph = networkx.DiGraph()
        graph.add_edge(create, obj)
        graph.add_edge(obj, delete)

        chains = self._strategy().generate(graph, [], filter_mutation_type=["DELETE"])
        all_last_nodes = {_names(c)[-1] for c in chains}
        assert "delete" not in all_last_nodes

    def test_filtered_ancestor_excluded_from_descendant_chain(self):
        """If an ancestor is filtered, it should be absent from the descendant chain."""
        update = _make_node("update", graphql_type="Mutation", mutation_type="UPDATE")
        obj = _make_node("Obj", graphql_type="Object")
        query = _make_node("getObj", graphql_type="Query")
        graph = networkx.DiGraph()
        graph.add_edge(update, obj)
        graph.add_edge(obj, query)

        chains = self._strategy().generate(graph, [], filter_mutation_type=["UPDATE"])
        chain_by_last = {_names(c)[-1]: _names(c) for c in chains}

        assert "update" not in chain_by_last
        q_chain = chain_by_last.get("getObj", [])
        assert "update" not in q_chain

    def test_starter_nodes_ignored(self):
        """TopologicalChainStrategy ignores starter_nodes; all nodes get a chain."""
        graph, nodes = _linear_graph("A", "B", "C")
        chains_empty = self._strategy().generate(graph, [])
        chains_with = self._strategy().generate(graph, [nodes[0]])
        assert len(chains_empty) == len(chains_with)

    def test_disable_mutations_excludes_all_mutations(self):
        original = config.DISABLE_MUTATIONS
        try:
            config.DISABLE_MUTATIONS = True
            graph = networkx.DiGraph()
            query = _make_node("getUser", graphql_type="Query")
            create = _make_node("createUser", graphql_type="Mutation", mutation_type="CREATE")
            graph.add_nodes_from([query, create])
            
            chains = self._strategy().generate(graph, [])
            for chain in chains:
                for node in chain.nodes:
                    assert node.graphql_type != "Mutation"
        finally:
            config.DISABLE_MUTATIONS = original
