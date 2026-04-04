"""Writes per-detection output files to the detections directory.

For every detection (confirmed or potential) two files are written under:
  <output_dir>/detections/<vuln_name>/<node_name>/

  raw_log.txt  - step-by-step request/response log up to the detection point.
  summary.txt  - concise summary: chain steps, final payload, and response.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from graphqler import config

if TYPE_CHECKING:
    from graphqler.chains.chain import Chain, ChainStep
    from graphqler.fuzzer.engine.types import Result


def _safe_name(name: str) -> str:
    """Sanitize a string so it is safe to use as a directory name."""
    return re.sub(r'[^\w\-]', '_', name).strip("_")


def _fmt_response(graphql_response: object) -> str:
    if isinstance(graphql_response, dict):
        return json.dumps(graphql_response, indent=2)
    return str(graphql_response)


def _detection_dir(vuln_name: str, node_name: str) -> Path:
    d = Path(config.OUTPUT_DIRECTORY) / config.DETECTIONS_DIR_NAME / _safe_name(vuln_name) / _safe_name(node_name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_from_detector(
    *,
    vuln_name: str,
    node_name: str,
    is_vulnerable: bool,
    potentially_vulnerable: bool,
    payload: str,
    graphql_response: object,
    status_code: int | None,
    evidence: str,
) -> None:
    """Write detection files for a standard (non-chain) detector finding.

    Nothing is written if neither ``is_vulnerable`` nor ``potentially_vulnerable``
    is True.
    """
    if not is_vulnerable and not potentially_vulnerable:
        return

    d = _detection_dir(vuln_name, node_name)
    status_str = "CONFIRMED" if is_vulnerable else "POTENTIAL"
    response_str = _fmt_response(graphql_response)

    # raw_log.txt — append one entry per detection event
    with open(d / "raw_log.txt", "a") as f:
        f.write(f"[DETECTION] {vuln_name}\n")
        f.write(f"[NODE] {node_name}\n")
        f.write(f"[STATUS] {status_str}\n")
        f.write(f"\nPayload:\n{payload}\n")
        f.write(f"\nHTTP Status: {status_code}\n")
        f.write(f"Response:\n{response_str}\n")
        f.write("\n" + "=" * 60 + "\n\n")

    # summary.txt — overwrite with latest finding
    with open(d / "summary.txt", "w") as f:
        f.write("=== Detection Summary ===\n")
        f.write(f"Vulnerability : {vuln_name}\n")
        f.write(f"Status        : {status_str}\n")
        f.write(f"Node          : {node_name}\n")
        if evidence:
            f.write(f"Evidence      : {evidence}\n")
        f.write(f"\n=== Payload ===\n{payload}\n")
        f.write(f"\n=== Response (HTTP {status_code}) ===\n{response_str}\n")


def write_from_chain(
    *,
    vuln_name: str,
    detected_node_name: str,
    chain: Chain,
    results: list[tuple[ChainStep, Result]],
    detected_step_index: int,
    evidence: str,
) -> None:
    """Write detection files for a chain-based detection (e.g. IDOR_CHAIN).

    ``results`` must contain the step/result pairs from chain execution.
    ``detected_step_index`` is the index within *results* that triggered the
    detection.  The raw log includes every step up to and including that index.
    """
    d = _detection_dir(vuln_name, detected_node_name)
    detected_step, detected_result = results[detected_step_index]
    final_payload = str(detected_result.payload)
    final_response = _fmt_response(detected_result.graphql_response)
    final_status = detected_result.status_code

    # raw_log.txt — append one entry per chain execution that fires detection
    with open(d / "raw_log.txt", "a") as f:
        f.write(f"[DETECTION] {vuln_name}\n")
        f.write(f"[CHAIN] {chain!r}\n")
        if chain.reason:
            f.write(f"[REASON] {chain.reason}\n")
        if chain.confidence:
            f.write(f"[CONFIDENCE] {chain.confidence}\n")
        f.write("\n")

        for i, (step, result) in enumerate(results[: detected_step_index + 1]):
            marker = "  <-- DETECTION POINT" if i == detected_step_index else ""
            f.write(f"[Step {i + 1}/{len(chain.steps)}] {step.node.name} [{step.profile_name}]{marker}\n")
            f.write(f"Payload:\n{result.payload}\n")
            f.write(f"HTTP Status: {result.status_code}\n")
            f.write(f"Response:\n{_fmt_response(result.graphql_response)}\n\n")

        f.write("=" * 60 + "\n\n")

    # summary.txt — overwrite with latest chain detection
    with open(d / "summary.txt", "w") as f:
        f.write("=== Detection Summary ===\n")
        f.write(f"Vulnerability : {vuln_name}\n")
        f.write("Status        : POTENTIAL\n")
        f.write(f"Node          : {detected_node_name}\n")
        if evidence:
            f.write(f"Evidence      : {evidence}\n")

        f.write("\n=== Chain ===\n")
        for i, step in enumerate(chain.steps):
            is_detected = (
                step.node.name == detected_node_name
                and step.profile_name == detected_step.profile_name
            )
            marker = "  <-- detected here" if is_detected else ""
            f.write(f"  {i + 1}. {step.node.name} [{step.profile_name}]{marker}\n")
        if chain.reason:
            f.write(f"\nReason     : {chain.reason}\n")
        if chain.confidence:
            f.write(f"Confidence : {chain.confidence}\n")

        f.write(f"\n=== Final Payload ===\n{final_payload}\n")
        f.write(f"\n=== Final Response (HTTP {final_status}) ===\n{final_response}\n")
