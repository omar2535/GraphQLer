"""UAF chain generation strategy."""

from __future__ import annotations

import logging

import networkx

from graphqler import config
from graphqler.chains.chain import Chain, ChainStep
from graphqler.chains.uaf import heuristic_uaf_classifier, llm_uaf_classifier
from graphqler.chains.strategies.base_strategy import BaseChainStrategy
from graphqler.graph.node import Node

logger = logging.getLogger(__name__)


class UAFChainStrategy(BaseChainStrategy):
    """Derives UAF (use-after-free / use-after-delete) candidate chains from regular chains.

    Takes already-generated chains and identifies those containing a
    CREATE → ... → DELETE → ... → ACCESS pattern.  Steps up to and including
    the DELETE are labelled ``"primary"``; post-delete access steps are labelled
    ``"post_delete"`` so the :class:`~graphqler.fuzzer.engine.detectors.UAFChainDetector`
    can flag successful responses as potential vulnerabilities.

    All steps execute under the primary auth token — UAF testing does not require
    a secondary credential because it tests whether the *same* user can re-access
    a resource they previously deleted.

    Enabled unless :attr:`~graphqler.config.SKIP_UAF_CHAIN_FUZZING` is ``True``.
    """

    file_name = "uaf.yml"

    def generate(self, graph: networkx.DiGraph | None, starter_nodes: list[Node],
                 source_chains: list[Chain] | None = None,
                 filter_mutation_type: list[str] | None = None) -> list[Chain]:
        """Evaluate *source_chains* and return UAF candidate chains.

        Two phases are executed in order:

        **Phase 1** — transform existing source chains that already contain the
        full ``CREATE → … → DELETE → … → ACCESS`` pattern (classified by heuristic
        or optional LLM fallback).

        **Phase 2** — synthesize new chains directly from *graph* edges.
        Because the topological strategy never places a DELETE mutation and a
        subsequent read query in the same chain (there is no dependency edge
        between them), Phase 1 rarely finds candidates for typical REST-style
        GraphQL APIs.  Phase 2 remedies this by looking up
        ``(CREATE c, Object o, DELETE d, Query r)`` quadruples where:

        * ``c → o`` (``c`` produces ``o``),
        * ``o → d`` (``d`` hard-depends on ``o``),
        * ``o → r`` (``r`` hard-depends on ``o``).

        The synthesised chain is ``c[primary] → o[primary] → d[primary] → r[post_delete]``.

        Args:
            graph (networkx.DiGraph | None): The dependency graph; used by Phase 2 synthesis.
                Passing ``None`` disables Phase 2.
            starter_nodes (list[Node]): Accepted for interface compatibility; not used.
            source_chains: Regular chains produced by a graph-based strategy.
            filter_mutation_type (list[str] | None): Accepted for interface compatibility; not used.

        Returns:
            A (possibly empty) list of chains where pre-delete steps are labelled
            ``"primary"`` and post-delete steps are labelled ``"post_delete"``.
            Returns an empty list immediately when UAF fuzzing is disabled.
        """
        if not self.is_enabled() or source_chains is None:
            return []

        candidates: list[Chain] = []

        for chain in source_chains:
            if not self._is_candidate(chain):
                continue

            confidence, split_index, reason = heuristic_uaf_classifier.classify(chain)
            logger.debug("Chain '%s' UAF heuristic score=%.2f split=%d reason='%s'",
                         chain.name, confidence, split_index, reason)

            if confidence >= config.UAF_HEURISTIC_CONFIDENCE_THRESHOLD:
                candidates.append(self._make_uaf_chain(chain, split_index, confidence,
                                                       f"heuristic: {reason}"))
                continue

            if config.UAF_USE_LLM_FALLBACK and config.USE_LLM and config.LLM_USE_FOR_COMPILATION:
                is_candidate, llm_reason = llm_uaf_classifier.classify(chain, split_index)
                if is_candidate:
                    effective_split = split_index if split_index > 0 else self._last_delete_split(chain)
                    if effective_split > 0:
                        candidates.append(self._make_uaf_chain(chain, effective_split, confidence,
                                                               f"llm: {llm_reason}"))
                        logger.debug("Chain '%s' accepted by LLM for UAF: %s", chain.name, llm_reason)
                else:
                    logger.debug("Chain '%s' rejected by LLM for UAF: %s", chain.name, llm_reason)

        # Phase 2: synthesize new chains from graph edges (CREATE → Object → DELETE + READ)
        if graph is not None:
            existing_keys = {"|".join(s.node.name for s in c.steps) for c in candidates}
            for synth_chain in self._synthesize_uaf_chains(graph):
                key = "|".join(s.node.name for s in synth_chain.steps)
                if key not in existing_keys:
                    candidates.append(synth_chain)
                    existing_keys.add(key)

        logger.info("UAFChainStrategy: %d UAF candidate chain(s) from %d total",
                    len(candidates), len(source_chains))
        return candidates

    def is_enabled(self) -> bool:
        """Return ``True`` when UAF chain generation is active."""
        return not config.SKIP_UAF_CHAIN_FUZZING

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _synthesize_uaf_chains(graph: networkx.DiGraph) -> list[Chain]:
        """Build UAF chains by finding ``(CREATE → Object → DELETE, READ)`` quadruples in the graph.

        Unlike Phase 1, which transforms existing chains that happen to contain the full
        CREATE→DELETE→ACCESS sequence, this method directly inspects graph edges.
        Because a DELETE mutation is never an ancestor of a READ query in the dependency
        graph (deleting a resource produces nothing useful for the subsequent read), the
        topological strategy never places them in the same chain.  This phase compensates
        by assembling the chain from the three constituent pieces found in the graph:

        1. A CREATE mutation ``c`` that produces Object ``o``
           (edge ``c → o`` via ``o.associatedMutations``).
        2. A DELETE mutation ``d`` that requires Object ``o``
           (edge ``o → d`` via ``d.hardDependsOn``).
        3. A Query ``r`` that requires Object ``o``
           (edge ``o → r`` via ``r.hardDependsOn``).

        The synthesized chain is:
        ``c[primary] → o[primary] → d[primary] → r[post_delete]``

        Args:
            graph: The compiled dependency graph.

        Returns:
            A list of synthesized UAF chains, one per valid quadruple discovered.
        """
        results: list[Chain] = []
        seen: set[str] = set()

        for delete_node in graph.nodes():
            if delete_node.mutation_type != "DELETE":
                continue

            object_preds = [n for n in graph.predecessors(delete_node) if n.graphql_type == "Object"]
            for obj_node in object_preds:
                create_preds = [n for n in graph.predecessors(obj_node) if n.mutation_type == "CREATE"]
                if not create_preds:
                    continue

                read_succs = [n for n in graph.successors(obj_node) if n.graphql_type == "Query"]
                if not read_succs:
                    continue

                for create_node in create_preds:
                    for read_node in read_succs:
                        key = f"{create_node.name}|{obj_node.name}|{delete_node.name}|{read_node.name}"
                        if key in seen:
                            continue
                        seen.add(key)

                        steps = [
                            ChainStep(node=create_node, profile_name="primary"),
                            ChainStep(node=obj_node, profile_name="primary"),
                            ChainStep(node=delete_node, profile_name="primary"),
                            ChainStep(node=read_node, profile_name="post_delete"),
                        ]
                        temp = Chain(steps=steps, name=key)
                        confidence, _, reason = heuristic_uaf_classifier.classify(temp)
                        results.append(Chain(
                            steps=steps,
                            name=key,
                            confidence=max(confidence, config.UAF_HEURISTIC_CONFIDENCE_THRESHOLD),
                            reason=f"synthesized: {reason or 'graph-derived uaf chain'}",
                        ))

        logger.info("UAFChainStrategy._synthesize: %d synthesized UAF chain(s)", len(results))
        return results

    @staticmethod
    def _is_candidate(chain: Chain) -> bool:
        """Quick pre-filter: skip chains that can never be UAF candidates."""
        if len(chain.steps) < 3:
            return False
        has_delete = any(step.node.mutation_type == "DELETE" for step in chain.steps)
        if not has_delete:
            return False
        # Ensure there is at least one node after the last DELETE
        last_delete = max(
            (i for i, step in enumerate(chain.steps) if step.node.mutation_type == "DELETE"),
            default=-1,
        )
        return last_delete < len(chain.steps) - 1

    @staticmethod
    def _last_delete_split(chain: Chain) -> int:
        """Return split_index = last DELETE index + 1, or 0 if no DELETE found."""
        idx = -1
        for i, step in enumerate(chain.steps):
            if step.node.mutation_type == "DELETE":
                idx = i
        return idx + 1 if idx >= 0 else 0

    @staticmethod
    def _make_uaf_chain(chain: Chain, split_index: int, confidence: float, reason: str) -> Chain:
        steps = []
        for i, step in enumerate(chain.steps):
            profile = "primary" if i < split_index else "post_delete"
            steps.append(ChainStep(node=step.node, profile_name=profile))

        return Chain(
            steps=steps,
            name=chain.name,
            confidence=confidence,
            reason=reason,
        )
