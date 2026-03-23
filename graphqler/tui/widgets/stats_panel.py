"""Live statistics display panel for the fuzz screen."""

import time

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label
from textual.containers import Horizontal


class StatsPanel(Widget):
    """Horizontal row of live stat counters updated during fuzzing."""

    DEFAULT_CSS = """
    StatsPanel {
        height: 5;
        border: solid $panel;
        margin-bottom: 1;
    }
    StatsPanel Horizontal {
        height: 1fr;
    }
    StatsPanel .stat-cell {
        width: 1fr;
        height: 1fr;
        border-right: solid $panel;
        content-align: center middle;
        padding: 0 1;
        layout: vertical;
    }
    StatsPanel .stat-label {
        text-align: center;
        color: $text-muted;
        height: 2;
        content-align: center middle;
    }
    StatsPanel .stat-value {
        text-align: center;
        text-style: bold;
        color: $accent;
        height: 3;
        content-align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            for stat_id, label in [
                ("stat-requests", "Requests"),
                ("stat-successes", "Successes"),
                ("stat-failures", "Failures"),
                ("stat-findings", "Findings"),
                ("stat-elapsed", "Elapsed"),
            ]:
                with Widget(classes="stat-cell"):
                    yield Label(label, classes="stat-label")
                    yield Label("0", id=stat_id, classes="stat-value")

    def update_from_stats(self, stats, start_time: float | None = None) -> None:
        """Refresh all counters from a Stats object."""
        totals = stats.number_of_successes + stats.number_of_failures
        self._set("stat-requests", str(totals))
        self._set("stat-successes", str(stats.number_of_successes))
        self._set("stat-failures", str(stats.number_of_failures))
        findings = len(stats.vulnerabilities) if stats.vulnerabilities else 0
        self._set("stat-findings", str(findings))
        if start_time is not None:
            elapsed = int(time.time() - start_time)
            mins, secs = divmod(elapsed, 60)
            self._set("stat-elapsed", f"{mins}m{secs:02d}s" if mins else f"{secs}s")

    def _set(self, widget_id: str, value: str) -> None:
        try:
            self.query_one(f"#{widget_id}", Label).update(value)
        except Exception:
            pass
