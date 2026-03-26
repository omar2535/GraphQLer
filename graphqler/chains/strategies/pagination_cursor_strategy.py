"""Pagination cursor attack chain generation strategy."""

from __future__ import annotations

import logging

import networkx

from graphqler import config
from graphqler.chains.chain import Chain, ChainStep
from graphqler.chains.cursor import heuristic_cursor_classifier
from graphqler.chains.strategies.base_strategy import BaseChainStrategy
from graphqler.graph.node import Node

logger = logging.getLogger(__name__)


class PaginationCursorStrategy(BaseChainStrategy):
    """Generates cursor-based attack chains for paginated GraphQL queries.

    For every Query node that the heuristic classifier identifies as a
    pagination endpoint, two types of chains may be generated:

    1. **Cursor injection chain** — two steps on the *same* node.
       Step 1 (``primary`` profile) fetches a real page to capture a live
       cursor into the objects bucket.  Step 2 (``cursor_injection`` profile)
       re-submits the query with the cursor decoded, mutated with SQL/NoSQL/
       path-traversal payloads, and re-encoded, probing whether the server
       interprets the cursor value as executable code.

    2. **Cursor IDOR chain** (opt-in) — same two-step structure but step 2
       uses the ``cursor_idor`` profile, which carries a different auth token.
       Generated only when :attr:`~graphqler.config.CURSOR_SECONDARY_AUTH` is
       set, so that the secondary user probes whether a shifted cursor leaks
       another user's data.

    Enabled unless :attr:`~graphqler.config.SKIP_CURSOR_CHAIN_FUZZING` is
    ``True``.
    """

    file_name = "pagination_cursor.yml"

    def generate(
        self,
        graph: networkx.DiGraph | None,
        starter_nodes: list[Node],
        source_chains: list[Chain] | None = None,
        filter_mutation_type: list[str] | None = None,
    ) -> list[Chain]:
        """Build cursor-attack chains for all pagination-candidate Query nodes.

        Args:
            graph: The compiled dependency graph.  Passing ``None`` disables
                this strategy (returns an empty list).
            starter_nodes: Accepted for interface compatibility; not used.
            source_chains: Accepted for interface compatibility; not used.
            filter_mutation_type: Accepted for interface compatibility; not used.

        Returns:
            A (possibly empty) list of cursor-attack chains.
        """
        if not self.is_enabled() or graph is None:
            return []

        candidates: list[Chain] = []

        for node in graph.nodes():
            if node.graphql_type != "Query":
                continue

            score, reason = heuristic_cursor_classifier.classify(node)
            if score < config.CURSOR_HEURISTIC_CONFIDENCE_THRESHOLD:
                continue

            logger.debug(
                "PaginationCursorStrategy: node '%s' score=%.2f reason='%s'",
                node.name,
                score,
                reason,
            )

            # Injection chain: step 1 fetches a real cursor; step 2 replays with mutated cursor
            candidates.append(
                Chain(
                    steps=[
                        ChainStep(node=node, profile_name="primary"),
                        ChainStep(node=node, profile_name="cursor_injection"),
                    ],
                    name=f"cursor_injection:{node.name}",
                    confidence=score,
                    reason=f"cursor injection chain: {reason}",
                )
            )

            # IDOR chain: same but step 2 probes cross-user access with secondary auth
            if config.CURSOR_SECONDARY_AUTH:
                candidates.append(
                    Chain(
                        steps=[
                            ChainStep(node=node, profile_name="primary"),
                            ChainStep(node=node, profile_name="cursor_idor"),
                        ],
                        name=f"cursor_idor:{node.name}",
                        confidence=score,
                        reason=f"cursor IDOR chain: {reason}",
                    )
                )

        logger.info(
            "PaginationCursorStrategy: %d cursor-attack chain(s) generated",
            len(candidates),
        )
        return candidates

    def is_enabled(self) -> bool:
        """Return ``True`` when cursor chain generation is active."""
        return not config.SKIP_CURSOR_CHAIN_FUZZING
