"""IDOR chain generation strategy."""

from __future__ import annotations

import logging

import networkx

from graphqler import config
from graphqler.chains.chain import Chain, ChainStep
from graphqler.chains.idor import heuristic_idor_classifier, llm_idor_classifier
from graphqler.chains.strategies.base_strategy import BaseChainStrategy
from graphqler.graph.node import Node

logger = logging.getLogger(__name__)


class IDORChainStrategy(BaseChainStrategy):
    """Derives IDOR candidate chains from an already-generated list of regular chains.

    Unlike graph-traversal strategies, this strategy takes the output of another
    strategy as input and classifies each chain for cross-user access-control weakness
    using a heuristic classifier with an optional LLM fallback.

    Only runs when :attr:`~graphqler.config.IDOR_SECONDARY_AUTH` is set and
    :attr:`~graphqler.config.SKIP_IDOR_CHAIN_FUZZING` is ``False``.
    """

    file_name = "idor.yml"

    def generate(self, graph: networkx.DiGraph, starter_nodes: list[Node],
                 source_chains: list[Chain] | None = None,
                 filter_mutation_type: list[str] | None = None) -> list[Chain]:
        """Evaluate *source_chains* and return IDOR candidate chains.

        Args:
            graph (networkx.DiGraph): Accepted for interface compatibility; not used.
            starter_nodes (list[Node]): Accepted for interface compatibility; not used.
            source_chains: Regular chains produced by a graph-based strategy.
            filter_mutation_type (list[str] | None): Accepted for interface compatibility; not used.

        Returns:
            A (possibly empty) list of chains where steps are associated with primary/secondary profiles.
            Returns an empty list immediately when IDOR secondary auth is not configured.
        """
        if not self.is_enabled() or source_chains is None:
            return []

        candidates: list[Chain] = []

        for chain in source_chains:
            if not self._is_candidate(chain):
                continue

            confidence, split_index, reason = heuristic_idor_classifier.classify(chain)
            logger.debug("Chain '%s' heuristic score=%.2f split=%d reason='%s'",
                         chain.name, confidence, split_index, reason)

            if confidence >= config.IDOR_HEURISTIC_CONFIDENCE_THRESHOLD:
                candidates.append(self._make_idor_chain(chain, split_index, confidence,
                                                        f"heuristic: {reason}"))
                continue

            if config.IDOR_USE_LLM_FALLBACK and config.USE_LLM:
                is_candidate, llm_reason = llm_idor_classifier.classify(chain, split_index)
                if is_candidate:
                    effective_split = split_index if split_index > 0 else self._last_create_split(chain)
                    if effective_split > 0:
                        candidates.append(self._make_idor_chain(chain, effective_split, confidence,
                                                                f"llm: {llm_reason}"))
                        logger.debug("Chain '%s' accepted by LLM: %s", chain.name, llm_reason)
                else:
                    logger.debug("Chain '%s' rejected by LLM: %s", chain.name, llm_reason)

        logger.info("IDORChainStrategy: %d IDOR candidate chain(s) from %d total",
                    len(candidates), len(source_chains))
        return candidates

    def is_enabled(self) -> bool:
        """Return ``True`` when IDOR chain generation is active."""
        return bool(config.IDOR_SECONDARY_AUTH) and not config.SKIP_IDOR_CHAIN_FUZZING

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _is_candidate(chain: Chain) -> bool:
        """Quick pre-filter: skip chains that can never be IDOR candidates."""
        if len(chain.steps) < 2:
            return False
        has_create = any(step.node.mutation_type == "CREATE" for step in chain.steps)
        if not has_create:
            return False
        last_create = max((i for i, step in enumerate(chain.steps) if step.node.mutation_type == "CREATE"),
                          default=-1)
        return last_create < len(chain.steps) - 1

    @staticmethod
    def _last_create_split(chain: Chain) -> int:
        """Return split_index = last CREATE index + 1, or 0 if no CREATE found."""
        idx = -1
        for i, step in enumerate(chain.steps):
            if step.node.mutation_type == "CREATE":
                idx = i
        return idx + 1 if idx >= 0 else 0

    @staticmethod
    def _make_idor_chain(chain: Chain, split_index: int, confidence: float, reason: str) -> Chain:
        steps = []
        for i, step in enumerate(chain.steps):
            profile = "primary" if i < split_index else "secondary"
            steps.append(ChainStep(node=step.node, profile_name=profile))

        return Chain(
            steps=steps,
            name=chain.name,
            confidence=confidence,
            reason=reason,
        )
