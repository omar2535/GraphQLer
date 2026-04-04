"""Scrolling log viewer widget with level-based coloring."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog

_LEVEL_STYLES: dict[str, str] = {
    "DEBUG": "dim",
    "INFO": "white",
    "WARNING": "yellow bold",
    "ERROR": "red bold",
    "CRITICAL": "red bold reverse",
}


class LogViewer(Widget):
    """A scrolling rich log widget that colors lines by log level."""

    DEFAULT_CSS = """
    LogViewer {
        height: 1fr;
        border: solid $panel;
    }
    """

    def compose(self) -> ComposeResult:
        yield RichLog(highlight=False, markup=True, wrap=True, id="inner-log")

    def write_line(self, text: str, level: str = "INFO") -> None:
        """Append a styled line to the log."""
        style = _LEVEL_STYLES.get(level.upper(), "white")
        try:
            rich_log = self.query_one("#inner-log", RichLog)
            rich_log.write(f"[{style}]{text}[/{style}]")
        except Exception:
            pass

    def clear(self) -> None:
        """Clear all log lines."""
        try:
            self.query_one("#inner-log", RichLog).clear()
        except Exception:
            pass
