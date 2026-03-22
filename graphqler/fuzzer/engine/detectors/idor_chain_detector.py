"""IDOR Chain Detector: Analyzes chain execution results for cross-user access-control weaknesses."""

import logging
from graphqler.chains.chain import Chain, ChainStep
from graphqler.fuzzer.engine.types import Result
from graphqler.utils import detection_writer
from graphqler.utils.stats import Stats

logger = logging.getLogger(__name__)


class IDORChainDetector:
    """Analyzes the results of a multi-profile chain execution to detect IDOR.

    A vulnerability is flagged if a step executed with the 'secondary' profile
    returns data that was (presumably) created or identified by steps executed
    with the 'primary' profile.

    .. note::
        This class intentionally does **not** extend :class:`~graphqler.fuzzer.engine.detectors.detector.Detector`.
        The ``Detector`` ABC is designed for single-node, single-request analysis: it receives one node,
        one materializer, and sends one request.  IDOR chain detection operates across an entire
        multi-step chain after all requests have already been executed, so it has a fundamentally
        different call site (``Fuzzer.__run_chain``) and a different interface (``detect(chain, results, stats)``).
        Forcing it into the ``Detector`` hierarchy would require significant compromises to both APIs.
    """

    def detect(self, chain: Chain, results: list[tuple[ChainStep, Result]], stats: Stats) -> None:
        """Analyze results and record any IDOR findings.

        Args:
            chain (Chain): The chain that was executed.
            results (list[tuple[ChainStep, Result]]): Execution results for each step.
            stats (Stats): The statistics object to record findings in.
        """
        if not chain.is_multi_profile:
            return

        for i, (step, result) in enumerate(results):
            if step.profile_name == "secondary" and result.success:
                evidence = f"Secondary auth token received data. Chain reason: {chain.reason}"
                logger.info(
                    f"[idor] POTENTIAL IDOR DETECTED on node '{step.node.name}' "
                    f"(chain reason: {chain.reason})"
                )
                stats.add_vulnerability(
                    "IDOR_CHAIN",
                    step.node.name,
                    is_vulnerable=False,
                    potentially_vulnerable=True,
                    evidence=evidence,
                )
                detection_writer.write_from_chain(
                    vuln_name="IDOR_CHAIN",
                    detected_node_name=step.node.name,
                    chain=chain,
                    results=results,
                    detected_step_index=i,
                    evidence=evidence,
                )
            elif step.profile_name == "secondary":
                logger.info(f"[idor] Node '{step.node.name}' correctly denied secondary token (not vulnerable)")
