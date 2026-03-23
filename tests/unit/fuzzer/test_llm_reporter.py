"""Unit tests for LLMReporter.

Covers:
- Reporter disabled when USE_LLM=False or LLM_ENABLE_REPORTER=False
- No-op when detections/ folder is absent
- Successful report generation path (LLM mocked)
- Graceful handling of LLM call failure
- Summary truncation and findings cap
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from graphqler.fuzzer.reporters.llm_reporter import LLMReporter, _MAX_FINDINGS_IN_REPORT, _MAX_SUMMARY_CHARS


def _make_detection(output_dir: Path, vuln: str, endpoint: str, text: str) -> None:
    """Helper: create a summary.txt under detections/<vuln>/<endpoint>/."""
    p = output_dir / "detections" / vuln / endpoint
    p.mkdir(parents=True, exist_ok=True)
    (p / "summary.txt").write_text(text, encoding="utf-8")


class TestLLMReporterDisabled(unittest.TestCase):
    """Reporter must return None immediately when toggled off."""

    def test_returns_none_when_use_llm_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("graphqler.fuzzer.reporters.llm_reporter.config") as mock_cfg:
                mock_cfg.USE_LLM = False
                mock_cfg.LLM_ENABLE_REPORTER = True
                reporter = LLMReporter(tmp, "http://localhost/graphql")
                result = reporter.generate()
        self.assertIsNone(result)

    def test_returns_none_when_reporter_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("graphqler.fuzzer.reporters.llm_reporter.config") as mock_cfg:
                mock_cfg.USE_LLM = True
                mock_cfg.LLM_ENABLE_REPORTER = False
                reporter = LLMReporter(tmp, "http://localhost/graphql")
                result = reporter.generate()
        self.assertIsNone(result)

    def test_returns_none_when_both_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("graphqler.fuzzer.reporters.llm_reporter.config") as mock_cfg:
                mock_cfg.USE_LLM = False
                mock_cfg.LLM_ENABLE_REPORTER = False
                reporter = LLMReporter(tmp, "http://localhost/graphql")
                result = reporter.generate()
        self.assertIsNone(result)


class TestLLMReporterNoDetections(unittest.TestCase):
    """Reporter must return None when no detections folder / files exist."""

    def test_no_detections_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("graphqler.fuzzer.reporters.llm_reporter.config") as mock_cfg:
                mock_cfg.USE_LLM = True
                mock_cfg.LLM_ENABLE_REPORTER = True
                reporter = LLMReporter(tmp, "http://localhost/graphql")
                result = reporter.generate()
        self.assertIsNone(result)

    def test_empty_detections_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "detections").mkdir()
            with patch("graphqler.fuzzer.reporters.llm_reporter.config") as mock_cfg:
                mock_cfg.USE_LLM = True
                mock_cfg.LLM_ENABLE_REPORTER = True
                reporter = LLMReporter(tmp, "http://localhost/graphql")
                result = reporter.generate()
        self.assertIsNone(result)


class TestLLMReporterGeneration(unittest.TestCase):
    """Reporter writes report.md when the LLM call succeeds."""

    def _mock_cfg(self, mock_cfg):
        mock_cfg.USE_LLM = True
        mock_cfg.LLM_ENABLE_REPORTER = True
        mock_cfg.LLM_MODEL = "gpt-4o-mini"
        mock_cfg.LLM_API_KEY = ""
        mock_cfg.LLM_BASE_URL = ""
        mock_cfg.LLM_REPORT_FILE_NAME = "report.md"

    def test_writes_report_on_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_detection(Path(tmp), "IDOR", "getUser", "User A can read User B's data.")

            with patch("graphqler.fuzzer.reporters.llm_reporter.config") as mock_cfg:
                self._mock_cfg(mock_cfg)
                mock_response = MagicMock()
                mock_response.choices[0].message.content = "# Report\n\nFindings here."
                with patch("graphqler.utils.llm_utils._get_litellm") as mock_get_litellm:
                    mock_litellm = MagicMock()
                    mock_litellm.completion.return_value = mock_response
                    mock_get_litellm.return_value = mock_litellm

                    reporter = LLMReporter(tmp, "http://localhost/graphql")
                    result = reporter.generate()

            self.assertIsNotNone(result)
            self.assertEqual(result.name, "report.md")
            self.assertTrue(result.exists())
            self.assertIn("Findings here", result.read_text())

    def test_returns_none_on_llm_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_detection(Path(tmp), "IDOR", "getUser", "Some finding.")

            with patch("graphqler.fuzzer.reporters.llm_reporter.config") as mock_cfg:
                self._mock_cfg(mock_cfg)
                with patch("graphqler.utils.llm_utils._get_litellm") as mock_get_litellm:
                    mock_litellm = MagicMock()
                    mock_litellm.completion.side_effect = RuntimeError("API down")
                    mock_get_litellm.return_value = mock_litellm

                    reporter = LLMReporter(tmp, "http://localhost/graphql")
                    result = reporter.generate()

        self.assertIsNone(result)


class TestLLMReporterTruncation(unittest.TestCase):
    """Verify per-summary truncation and findings cap are applied."""

    def test_summary_truncated(self):
        reporter = LLMReporter("/tmp", "http://localhost/graphql")
        long_summary = "x" * (_MAX_SUMMARY_CHARS + 500)
        summaries = [{"vuln_name": "IDOR", "node_name": "getUser", "summary": long_summary}]
        result = reporter._format_findings(summaries)
        self.assertIn("[truncated]", result)
        self.assertLessEqual(len(result), _MAX_SUMMARY_CHARS + 200)

    def test_short_summary_not_truncated(self):
        reporter = LLMReporter("/tmp", "http://localhost/graphql")
        short = "Short finding."
        summaries = [{"vuln_name": "IDOR", "node_name": "getUser", "summary": short}]
        result = reporter._format_findings(summaries)
        self.assertNotIn("[truncated]", result)
        self.assertIn("Short finding.", result)

    def test_findings_capped_in_generate(self):
        """generate() should cap summaries at _MAX_FINDINGS_IN_REPORT."""
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(_MAX_FINDINGS_IN_REPORT + 5):
                _make_detection(Path(tmp), "IDOR", f"endpoint_{i}", f"Finding {i}")

            with patch("graphqler.fuzzer.reporters.llm_reporter.config") as mock_cfg:
                mock_cfg.USE_LLM = True
                mock_cfg.LLM_ENABLE_REPORTER = True
                mock_cfg.LLM_MODEL = "gpt-4o-mini"
                mock_cfg.LLM_API_KEY = ""
                mock_cfg.LLM_BASE_URL = ""
                mock_cfg.LLM_REPORT_FILE_NAME = "report.md"

                captured: list = []

                def fake_format(summaries):
                    captured.extend(summaries)
                    return "findings"

                mock_response = MagicMock()
                mock_response.choices[0].message.content = "# Report"
                with patch("graphqler.utils.llm_utils._get_litellm") as mock_get_litellm:
                    mock_litellm = MagicMock()
                    mock_litellm.completion.return_value = mock_response
                    mock_get_litellm.return_value = mock_litellm

                    reporter = LLMReporter(tmp, "http://localhost/graphql")
                    reporter._format_findings = fake_format
                    reporter.generate()

        self.assertEqual(len(captured), _MAX_FINDINGS_IN_REPORT)


if __name__ == "__main__":
    unittest.main()
