"""UAF Chain Detector: Analyzes chain execution results for use-after-delete vulnerabilities."""

import logging
from graphqler.chains.chain import Chain, ChainStep
from graphqler.fuzzer.engine.types import Result
from graphqler.utils import detection_writer
from graphqler.utils.stats import Stats

logger = logging.getLogger(__name__)


class UAFChainDetector:
    """Analyzes the results of a UAF chain execution to detect use-after-delete vulnerabilities.

    A vulnerability is flagged if a step executed with the ``'post_delete'`` profile
    returns a successful data response — meaning the API still serves the resource
    even though it was previously deleted.

    .. note::
        Like :class:`~graphqler.fuzzer.engine.detectors.IDORChainDetector`, this class
        intentionally does **not** extend
        :class:`~graphqler.fuzzer.engine.detectors.detector.Detector`.
        UAF detection operates across an entire multi-step chain after all requests
        have already been executed, so it has a fundamentally different call site and
        interface from the single-node ``Detector`` hierarchy.
    """

    def detect(self, chain: Chain, results: list[tuple[ChainStep, Result]], stats: Stats) -> None:
        """Analyze results and record any UAF findings.

        Args:
            chain (Chain): The chain that was executed.
            results (list[tuple[ChainStep, Result]]): Execution results for each step.
            stats (Stats): The statistics object to record findings in.
        """
        has_post_delete = any(step.profile_name == "post_delete" for step, _ in results)
        if not has_post_delete:
            return

        for i, (step, result) in enumerate(results):
            node_data = result.data.get(step.node.name)
            if step.profile_name == "post_delete" and result.success and node_data not in (None, {}, []):
                evidence = f"Resource still accessible after deletion. Chain reason: {chain.reason}"
                logger.info(
                    f"[uaf] POTENTIAL UAF DETECTED on node '{step.node.name}' "
                    f"(chain reason: {chain.reason})"
                )
                stats.add_vulnerability(
                    "UAF_CHAIN",
                    step.node.name,
                    is_vulnerable=True,
                    potentially_vulnerable=True,
                    evidence=evidence,
                )
                detection_writer.write_from_chain(
                    vuln_name="UAF_CHAIN",
                    detected_node_name=step.node.name,
                    chain=chain,
                    results=results,
                    detected_step_index=i,
                    evidence=evidence,
                )
            elif step.profile_name == "post_delete":
                logger.info(f"[uaf] Node '{step.node.name}' correctly rejected post-delete access (not vulnerable)")
