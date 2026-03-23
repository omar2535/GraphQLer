"""LLM-powered vulnerability report generator.

After fuzzing, ``LLMReporter.generate()`` reads every detection ``summary.txt``
from the ``detections/`` folder, synthesises them with the LLM, and writes a
human-readable Markdown pentest report to the output directory.

The report contains:
  - An executive summary paragraph
  - A severity-ranked vulnerability table
  - Per-vulnerability sections with description, evidence, and remediation advice

Controlled by ``config.USE_LLM``.  When False (the default), or when no
detections exist, ``generate()`` returns immediately without making any LLM call.
"""

from __future__ import annotations

import logging
from pathlib import Path

from graphqler import config
from graphqler.utils import llm_utils

logger = logging.getLogger(__name__)

# ── Prompt templates ──────────────────────────────────────────────────────────

_REPORT_SYSTEM_PROMPT = """\
You are an expert application security engineer writing a professional penetration test report.
You will be given a list of GraphQL API vulnerability findings discovered by an automated fuzzer.
Write a clear, concise Markdown report that a developer can act on immediately.

Your report MUST follow this exact structure:

## Executive Summary
<One paragraph summarising the overall security posture and the most critical findings.>

## Vulnerability Summary

| # | Vulnerability | Severity | Affected Endpoint(s) |
|---|---------------|----------|----------------------|
<One row per finding, ordered critical → high → medium → low → informational.>

## Findings

### [VulnName] — [Severity]
**Affected endpoint(s):** …
**Description:** …
**Evidence:** …
**Remediation:** …

<Repeat for each finding.>

## Conclusion
<Brief closing paragraph with overall recommendation.>

Rules:
- Use only the evidence provided — do not invent findings.
- Severity must be one of: Critical, High, Medium, Low, Informational.
- Keep each finding section concise (3–6 sentences per sub-field).
- Do NOT wrap the report in a code fence — return raw Markdown.\
"""

_REPORT_USER_PROMPT_TEMPLATE = """\
The fuzzer scanned: {url}

Detections found ({count} total):

{findings_text}

Write the penetration test report.\
"""


# ── LLMReporter ───────────────────────────────────────────────────────────────

class LLMReporter:
    """Generate a Markdown pentest report from fuzzer detection summaries.

    Args:
        output_dir (str | Path): The fuzzer output directory that contains the
            ``detections/`` sub-folder and where ``report.md`` will be written.
        url (str): The target GraphQL URL (included in the report header).
    """

    def __init__(self, output_dir: str | Path, url: str = ""):
        self.output_dir = Path(output_dir)
        self.url = url or "unknown"

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(self) -> Path | None:
        """Read detections, call the LLM, and write ``report.md``.

        Returns:
            Path to the written report, or ``None`` if the report was skipped
            (LLM disabled, no detections, or any error).
        """
        if not config.USE_LLM:
            logger.debug("LLMReporter: USE_LLM=False — skipping report generation.")
            return None

        summaries = self._collect_summaries()
        if not summaries:
            logger.info("LLMReporter: no detections found — skipping report generation.")
            return None

        logger.info("LLMReporter: generating report from %d detection(s) …", len(summaries))

        findings_text = self._format_findings(summaries)
        user_prompt = _REPORT_USER_PROMPT_TEMPLATE.format(
            url=self.url,
            count=len(summaries),
            findings_text=findings_text,
        )

        try:
            # The report is Markdown prose, not JSON — we capture raw text here.
            report_md = self._call_llm_for_text(_REPORT_SYSTEM_PROMPT, user_prompt)
        except Exception as exc:
            logger.warning("LLMReporter: LLM call failed: %s", exc)
            return None

        return self._write_report(report_md)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _collect_summaries(self) -> list[dict[str, str]]:
        """Walk ``detections/`` and collect every ``summary.txt`` content.

        Returns:
            List of dicts with keys ``vuln_name``, ``node_name``, ``summary``.
        """
        detections_dir = self.output_dir / "detections"
        if not detections_dir.is_dir():
            return []

        results: list[dict[str, str]] = []
        for vuln_dir in sorted(detections_dir.iterdir()):
            if not vuln_dir.is_dir():
                continue
            for node_dir in sorted(vuln_dir.iterdir()):
                if not node_dir.is_dir():
                    continue
                summary_file = node_dir / "summary.txt"
                if summary_file.exists():
                    results.append({
                        "vuln_name": vuln_dir.name,
                        "node_name": node_dir.name,
                        "summary": summary_file.read_text(encoding="utf-8", errors="replace").strip(),
                    })
        return results

    def _format_findings(self, summaries: list[dict[str, str]]) -> str:
        """Convert detection summary dicts into a readable block for the LLM prompt."""
        blocks: list[str] = []
        for i, s in enumerate(summaries, start=1):
            blocks.append(
                f"--- Finding {i} ---\n"
                f"Vulnerability type: {s['vuln_name']}\n"
                f"Affected endpoint:  {s['node_name']}\n"
                f"Summary:\n{s['summary']}"
            )
        return "\n\n".join(blocks)

    def _call_llm_for_text(self, system_prompt: str, user_prompt: str) -> str:
        """Call the LLM and return raw text (not JSON).

        Uses litellm directly so the retry/JSON logic in ``llm_utils.call_llm``
        does not interfere with Markdown output.
        """
        litellm = llm_utils._get_litellm()

        kwargs: dict = {"model": config.LLM_MODEL}
        if config.LLM_API_KEY:
            kwargs["api_key"] = config.LLM_API_KEY
        if config.LLM_BASE_URL:
            kwargs["base_url"] = config.LLM_BASE_URL

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = litellm.completion(**{**kwargs, "messages": messages})
        return response.choices[0].message.content or ""

    def _write_report(self, content: str) -> Path:
        """Write ``content`` to ``output_dir/report.md`` and return the path."""
        report_path = self.output_dir / config.LLM_REPORT_FILE_NAME
        report_path.write_text(content, encoding="utf-8")
        logger.info("LLMReporter: report written to %s", report_path)
        return report_path
