"""Bridges Python's logging system to the TUI log viewer widget.

When the TUI is active this handler is installed on the root logger so that
all existing logging calls (compiler, fuzzer, etc.) are automatically forwarded
to the on-screen log viewer without any changes to the logging callsites.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from graphqler.tui.app import GraphQLerApp


class TUILogHandler(logging.Handler):
    """Forwards log records to the TUI LogViewer widget via call_from_thread."""

    def __init__(self, app: "GraphQLerApp") -> None:
        super().__init__()
        self._app = app
        self.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            text = self.format(record)
            self._app.call_from_thread(self._app.add_log_line, text, record.levelname)
        except Exception:
            self.handleError(record)
