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

    def generate(self, graph: networkx.DiGraph, starter_nodes: list[Node],
                 source_chains: list[Chain] | None = None,
                 filter_mutation_type: list[str] | None = None) -> list[Chain]:
        """Evaluate *source_chains* and return UAF candidate chains.

        Args:
            graph (networkx.DiGraph): Accepted for interface compatibility; not used.
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

            if config.UAF_USE_LLM_FALLBACK and config.USE_LLM:
                is_candidate, llm_reason = llm_uaf_classifier.classify(chain, split_index)
                if is_candidate:
                    effective_split = split_index if split_index > 0 else self._last_delete_split(chain)
                    if effective_split > 0:
                        candidates.append(self._make_uaf_chain(chain, effective_split, confidence,
                                                               f"llm: {llm_reason}"))
                        logger.debug("Chain '%s' accepted by LLM for UAF: %s", chain.name, llm_reason)
                else:
                    logger.debug("Chain '%s' rejected by LLM for UAF: %s", chain.name, llm_reason)

        logger.info("UAFChainStrategy: %d UAF candidate chain(s) from %d total",
                    len(candidates), len(source_chains))
        return candidates

    def is_enabled(self) -> bool:
        """Return ``True`` when UAF chain generation is active."""
        return not config.SKIP_UAF_CHAIN_FUZZING

    # ── Helpers ──────────────────────────────────────────────────────────────

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
