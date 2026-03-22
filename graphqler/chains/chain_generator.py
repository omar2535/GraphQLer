"""ChainGenerator: generates, saves, and loads dependency chains."""

from pathlib import Path

import networkx
import yaml

from graphqler import config
from graphqler.chains.chain import Chain
from graphqler.graph.node import Node


class ChainGenerator:
    """Generates, saves, and loads dependency chains.

    The generator is strategy-agnostic: callers (e.g. the :class:`~graphqler.compiler.Compiler`)
    decide which strategies to use and call :meth:`generate_with_strategy` once per strategy.
    Results accumulate across calls so that :meth:`save_to_yaml` writes all of them at once.

    Usage::

        generator = ChainGenerator()
        regular_chains = generator.generate_with_strategy(TopologicalChainStrategy(), graph, starter_nodes)
        generator.generate_with_strategy(IDORChainStrategy(), regular_chains)
        generator.save_to_yaml(output_path)
    """

    def __init__(self):
        self._chains: list[Chain] = []
        self._results: list[tuple[object, list[Chain]]] = []

    @property
    def chains(self) -> list[Chain]:
        """All chains accumulated across all :meth:`generate_with_strategy` calls."""
        return self._chains

    def generate_with_strategy(self, strategy, *args) -> list[Chain]:
        """Run *strategy* and accumulate its output.

        The positional *args* are forwarded directly to ``strategy.generate(*args)``,
        so any strategy signature is supported.

        Args:
            strategy: Any object with a ``generate(*args) -> list[Chain]`` method
                      and a ``file_name: str`` attribute.
            *args: Arguments forwarded to ``strategy.generate``.

        Returns:
            list[Chain]: The chains produced by this strategy call.
        """
        chains = strategy.generate(*args)
        self._results.append((strategy, chains))
        self._chains.extend(chains)
        return chains

    def save_to_yaml(self, save_path: str) -> None:
        """Persist each strategy's chains to its own YAML file under ``<save_path>/compiled/chains/``.

        The filename is taken from ``strategy.file_name``.
        Regular chains are stored as ``{nodes: [...names...]}``.
        IDOR chains additionally include ``idor_split_index``, ``idor_confidence``,
        and ``idor_reason``.

        Args:
            save_path (str): Root output directory.
        """
        chains_dir = Path(save_path) / config.CHAINS_DIR_NAME
        chains_dir.mkdir(parents=True, exist_ok=True)

        for strategy, chains in self._results:
            data = []
            for chain in chains:
                entry: dict = {"nodes": [n.name for n in chain.nodes]}
                if chain.split_index is not None:
                    entry["idor_split_index"] = chain.split_index
                    entry["idor_confidence"] = round(chain.confidence, 4)
                    entry["idor_reason"] = chain.reason
                data.append(entry)
            with open(chains_dir / strategy.file_name, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def load_from_yaml(self, save_path: str, graph: networkx.DiGraph) -> list[Chain]:
        """Load chains from all YAML files under ``<save_path>/compiled/chains/``.

        Entries containing ``idor_split_index`` are restored as chains with
        ``split_index`` set; all others become regular :class:`Chain` objects.

        Args:
            save_path (str): Root output directory.
            graph (networkx.DiGraph): The dependency graph used to look up Node objects.

        Returns:
            list[Chain]: The loaded chains.
        """
        chains_dir = Path(save_path) / config.CHAINS_DIR_NAME
        if not chains_dir.exists():
            self._chains = []
            return self._chains

        node_map: dict[str, Node] = {node.name: node for node in graph.nodes()}
        chains: list[Chain] = []

        for chain_file in sorted(chains_dir.glob("*.yml")):
            with open(chain_file, "r") as f:
                data = yaml.safe_load(f) or []
            for entry in data:
                nodes = [node_map[name] for name in entry.get("nodes", []) if name in node_map]
                if "idor_split_index" in entry:
                    chains.append(Chain(
                        nodes=nodes,
                        split_index=entry["idor_split_index"],
                        confidence=entry.get("idor_confidence", 0.0),
                        reason=entry.get("idor_reason", ""),
                    ))
                else:
                    chains.append(Chain(nodes=nodes))

        self._chains = chains
        return self._chains
