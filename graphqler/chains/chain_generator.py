"""ChainGenerator: orchestrates chain generation using a pluggable strategy."""

from pathlib import Path

import networkx
import yaml

from graphqler import config
from graphqler.chains.chain import Chain
from graphqler.chains.strategies.base_strategy import BaseChainStrategy
from graphqler.chains.strategies.topological_strategy import TopologicalChainStrategy
from graphqler.graph.node import Node

# All possible mutation_type values assigned to Mutation nodes
_ALL_MUTATION_TYPES = ["CREATE", "UPDATE", "DELETE", "UNKNOWN"]


class ChainGenerator:
    """Generates and stores dependency chains for later inspection and fuzzer consumption.

    The generator applies a **3-pass** strategy (mirroring the original DFS passes) when
    ``config.DISABLE_MUTATIONS`` is ``False`` (the default):

    * **Pass 1** — chains containing only CREATE / QUERY nodes (UPDATE, DELETE, UNKNOWN filtered out)
    * **Pass 2** — chains allowing CREATE, QUERY, and UPDATE (DELETE, UNKNOWN filtered out)
    * **Pass 3** — all chains (no filter)

    All three passes are concatenated into a single list so that the fuzzer can simply
    iterate through ``chains`` without any additional filtering.

    When ``config.DISABLE_MUTATIONS`` is ``True``, only Query (and Object) chains are
    produced — all mutation nodes are excluded entirely.

    Usage::

        generator = ChainGenerator()
        chains = generator.generate(dependency_graph, starter_nodes)
        # chains are also accessible afterwards:
        print(generator.chains)

    The default strategy is :class:`TopologicalChainStrategy`.  Pass a different
    :class:`BaseChainStrategy` subclass to use an alternative generation method
    (e.g. :class:`~graphqler.chains.strategies.dfs_strategy.DFSChainStrategy`).
    """

    def __init__(self, strategy: BaseChainStrategy | None = None):
        """Initialise the generator with an optional strategy.

        Args:
            strategy (BaseChainStrategy | None): Chain generation strategy.
                Defaults to :class:`DFSChainStrategy` when *None*.
        """
        self._strategy: BaseChainStrategy = strategy if strategy is not None else TopologicalChainStrategy()
        self._chains: list[Chain] = []

    @property
    def chains(self) -> list[Chain]:
        """The chains produced by the most recent :meth:`generate` call (empty until then)."""
        return self._chains

    def generate(self, graph: networkx.DiGraph, starter_nodes: list[Node]) -> list[Chain]:
        """Generate chains and store them for later inspection.

        Applies the 3-pass filtering strategy internally so that the fuzzer receives a
        single ordered list of chains ready to execute sequentially.

        Args:
            graph (networkx.DiGraph): The compiled dependency graph.
            starter_nodes (list[Node]): Root nodes to start generation from.

        Returns:
            list[Chain]: The generated chains (same object as :attr:`chains`).
        """
        if config.DISABLE_MUTATIONS:
            # Only produce chains that contain Query/Object nodes — exclude all mutations
            self._chains = self._strategy.generate(
                graph, starter_nodes, filter_mutation_type=_ALL_MUTATION_TYPES
            )
        else:
            # Pass 1: CREATE + QUERY only (filter UPDATE, DELETE, UNKNOWN)
            pass1 = self._strategy.generate(
                graph, starter_nodes,
                filter_mutation_type=["UPDATE", "DELETE", "UNKNOWN"],
            )
            # Pass 2: CREATE + QUERY + UPDATE (filter DELETE, UNKNOWN)
            pass2 = self._strategy.generate(
                graph, starter_nodes,
                filter_mutation_type=["DELETE", "UNKNOWN"],
            )
            # Pass 3: all nodes
            pass3 = self._strategy.generate(
                graph, starter_nodes,
                filter_mutation_type=[],
            )
            self._chains = pass1 + pass2 + pass3

        return self._chains

    def save_to_yaml(self, save_path: str) -> None:
        """Persist the generated chains to a YAML file for human inspection and optional editing.

        Each chain is stored as a list of node names.  On reload the names are
        resolved back to :class:`~graphqler.graph.node.Node` objects using the
        dependency graph.

        Args:
            save_path (str): Root output directory (same directory used for compilation).
        """
        chains_path = Path(save_path) / config.CHAINS_FILE_NAME
        chains_path.parent.mkdir(parents=True, exist_ok=True)
        data = [{"nodes": [n.name for n in chain.nodes]} for chain in self._chains]
        with open(chains_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def load_from_yaml(self, save_path: str, graph: networkx.DiGraph) -> list[Chain]:
        """Load chains from a previously saved YAML file and populate :attr:`chains`.

        Node names in the YAML are resolved to :class:`~graphqler.graph.node.Node`
        objects using *graph*.  Any name that no longer exists in the graph is
        silently skipped so that hand-edited files do not crash the fuzzer.

        Args:
            save_path (str): Root output directory (same directory used for compilation).
            graph (networkx.DiGraph): The dependency graph used to look up Node objects.

        Returns:
            list[Chain]: The loaded chains (same object as :attr:`chains`).
        """
        chains_path = Path(save_path) / config.CHAINS_FILE_NAME
        if not chains_path.exists():
            self._chains = []
            return self._chains

        node_map: dict[str, Node] = {node.name: node for node in graph.nodes()}
        with open(chains_path, "r") as f:
            data = yaml.safe_load(f) or []

        self._chains = [
            Chain(nodes=[node_map[name] for name in entry.get("nodes", []) if name in node_map])
            for entry in data
        ]
        return self._chains

