"""ChainGenerator: generates, saves, and loads dependency chains."""

from pathlib import Path

import networkx
import yaml

from graphqler import config
from graphqler.chains.chain import Chain, ChainStep
from graphqler.chains.strategies.base_strategy import BaseChainStrategy
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
        self._results: list[tuple[BaseChainStrategy, list[Chain]]] = []

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
        Regular chains are stored as a list of steps, each with a node name and a profile name.

        Args:
            save_path (str): Root output directory.
        """
        chains_dir = Path(save_path) / config.CHAINS_DIR_NAME
        chains_dir.mkdir(parents=True, exist_ok=True)

        for strategy, chains in self._results:
            data = []
            for chain in chains:
                entry: dict = {
                    "steps": [{"node": step.node.name, "profile": step.profile_name} for step in chain.steps],
                    "confidence": round(chain.confidence, 4),
                    "reason": chain.reason,
                }
                data.append(entry)
            with open(chains_dir / strategy.file_name, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def load_from_yaml(self, save_path: str, graph: networkx.DiGraph) -> list[Chain]:
        """Load chains from all YAML files under ``<save_path>/compiled/chains/``.

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
                steps = []
                # Handle new format (list of steps)
                if "steps" in entry:
                    for step_data in entry["steps"]:
                        node_name = step_data["node"]
                        profile_name = step_data.get("profile", step_data.get("context", "primary"))
                        if node_name in node_map:
                            steps.append(ChainStep(node=node_map[node_name], profile_name=profile_name))
                # Handle old format (flat list of nodes) for backward compatibility during transition
                elif "nodes" in entry:
                    split_index = entry.get("idor_split_index")
                    for i, node_name in enumerate(entry["nodes"]):
                        if node_name in node_map:
                            profile = "primary"
                            if split_index is not None and i >= split_index:
                                profile = "secondary"
                            steps.append(ChainStep(node=node_map[node_name], profile_name=profile))

                if steps:
                    chains.append(Chain(
                        steps=steps,
                        confidence=entry.get("idor_confidence", entry.get("confidence", 1.0)),
                        reason=entry.get("idor_reason", entry.get("reason", "")),
                    ))

        self._chains = chains
        return self._chains
