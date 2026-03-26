"""CursorChainDetector: analyses chain results for cursor-based vulnerabilities."""

from __future__ import annotations

import logging
import re

from graphqler.chains.chain import Chain, ChainStep
from graphqler.fuzzer.engine.types import Result
from graphqler.utils import detection_writer
from graphqler.utils.stats import Stats

logger = logging.getLogger(__name__)

# ── Error-pattern regexes ─────────────────────────────────────────────────────

_SQL_ERROR_PATTERN = re.compile(
    r"(sql\s+syntax|mysql_fetch|ora-\d{4,}|pg_query|sqlite_query|"
    r"unclosed quotation|syntax error|unexpected token|sql exception|"
    r"sqlstate|odbc driver|jdbc)",
    re.IGNORECASE,
)

_NOSQL_ERROR_PATTERN = re.compile(
    r"(mongod|bson|mongodb|cassandra|redis|dynamo|"
    r"json parse error|unexpected end of json)",
    re.IGNORECASE,
)


class CursorChainDetector:
    """Analyses the results of a cursor-attack chain for injection and IDOR findings.

    Two vulnerability classes are checked:

    * ``CURSOR_IDOR`` — the step executed with the ``cursor_idor`` profile
      returned a non-empty data payload, meaning the server returned data when
      the cursor was shifted to probe another user's resource.

    * ``CURSOR_INJECTION`` — the step executed with the ``cursor_injection``
      profile triggered a SQL/NoSQL error pattern or returned an HTTP 500,
      suggesting the cursor value is being interpreted as executable code.

    .. note::
        Like :class:`~graphqler.fuzzer.engine.detectors.UAFChainDetector` and
        :class:`~graphqler.fuzzer.engine.detectors.IDORChainDetector`, this
        class does **not** extend the single-node ``Detector`` ABC.  Cursor
        detection operates across a completed multi-step chain and has a
        different call site (``Fuzzer.__run_chain``).
    """

    def detect(
        self,
        chain: Chain,
        results: list[tuple[ChainStep, Result]],
        stats: Stats,
    ) -> None:
        """Analyse *results* and record any cursor-attack findings.

        Args:
            chain: The chain that was executed.
            results: Execution results for each step, in order.
            stats: The statistics singleton to record findings in.
        """
        has_cursor_step = any(
            step.profile_name in ("cursor_injection", "cursor_idor")
            for step, _ in results
        )
        if not has_cursor_step:
            return

        for i, (step, result) in enumerate(results):
            if step.profile_name == "cursor_idor":
                self._check_cursor_idor(chain, step, result, results, i, stats)
            elif step.profile_name == "cursor_injection":
                self._check_cursor_injection(chain, step, result, results, i, stats)

    # ── Private helpers ────────────────────────────────────────────────────────

    def _check_cursor_idor(
        self,
        chain: Chain,
        step: ChainStep,
        result: Result,
        results: list[tuple[ChainStep, Result]],
        step_index: int,
        stats: Stats,
    ) -> None:
        """Flag CURSOR_IDOR when the secondary token received data via a shifted cursor."""
        node_data = result.data.get(step.node.name) if result.data else None
        if result.success and node_data not in (None, {}, []):
            evidence = (
                f"Secondary auth token received data via mutated cursor. "
                f"Chain reason: {chain.reason}"
            )
            logger.info(
                "[cursor] POTENTIAL CURSOR IDOR on node '%s' (chain: %s)",
                step.node.name,
                chain.reason,
            )
            stats.add_vulnerability(
                "CURSOR_IDOR",
                step.node.name,
                is_vulnerable=False,
                potentially_vulnerable=True,
                evidence=evidence,
            )
            detection_writer.write_from_chain(
                vuln_name="CURSOR_IDOR",
                detected_node_name=step.node.name,
                chain=chain,
                results=results,
                detected_step_index=step_index,
                evidence=evidence,
            )
        else:
            logger.info(
                "[cursor] Node '%s' did not return cross-user data via cursor (not IDOR vulnerable)",
                step.node.name,
            )

    def _check_cursor_injection(
        self,
        chain: Chain,
        step: ChainStep,
        result: Result,
        results: list[tuple[ChainStep, Result]],
        step_index: int,
        stats: Stats,
    ) -> None:
        """Flag CURSOR_INJECTION when an injected cursor triggered a backend error."""
        raw_text: str = getattr(result, "raw_response_text", "") or ""
        status_code: int = getattr(result, "status_code", 0) or 0

        injection_detected = (
            status_code == 500
            or bool(_SQL_ERROR_PATTERN.search(raw_text))
            or bool(_NOSQL_ERROR_PATTERN.search(raw_text))
        )

        if injection_detected:
            evidence = (
                f"Injected cursor triggered a backend error (HTTP {status_code}). "
                f"Chain reason: {chain.reason}. "
                f"Response snippet: {raw_text[:300]!r}"
            )
            logger.info(
                "[cursor] POTENTIAL CURSOR INJECTION on node '%s' (HTTP %d)",
                step.node.name,
                status_code,
            )
            stats.add_vulnerability(
                "CURSOR_INJECTION",
                step.node.name,
                is_vulnerable=False,
                potentially_vulnerable=True,
                evidence=evidence,
            )
            detection_writer.write_from_chain(
                vuln_name="CURSOR_INJECTION",
                detected_node_name=step.node.name,
                chain=chain,
                results=results,
                detected_step_index=step_index,
                evidence=evidence,
            )
        else:
            logger.info(
                "[cursor] Node '%s' did not show injection signals for mutated cursor (not vulnerable)",
                step.node.name,
            )
