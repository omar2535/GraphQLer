"""Main Textual application entry point for the GraphQLer TUI."""

import builtins

from textual.app import App


class GraphQLerApp(App):
    """Root Textual application; manages screen navigation and stdout capture."""

    TITLE = "GraphQLer"
    SUB_TITLE = "GraphQL API Fuzzer & Security Testing Tool"
    CSS_PATH = "graphqler.tcss"
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_print = None

    def on_mount(self) -> None:
        from graphqler.tui.screens.home_screen import HomeScreen

        self._install_print_capture()
        self.push_screen(HomeScreen())

    def on_unmount(self) -> None:
        self._restore_print()

    def _install_print_capture(self) -> None:
        """Replace builtins.print with a version that forwards to the LogViewer.

        Only plain print() calls (to stdout) are captured; explicit file= writes
        (e.g. print(..., file=sys.stderr)) use the original print unchanged.
        """
        import sys

        app = self
        self._original_print = builtins.print

        def _tui_print(*args, sep: str = " ", end: str = "\n", file=None, flush: bool = False) -> None:
            if file is not None and file is not sys.stdout:
                app._original_print(*args, sep=sep, end=end, file=file, flush=flush)
                return
            text = sep.join(str(a) for a in args)
            if text:
                try:
                    app.call_from_thread(app.add_log_line, text, "INFO")
                except Exception:
                    app._original_print(text)

        builtins.print = _tui_print

    def _restore_print(self) -> None:
        if self._original_print is not None:
            builtins.print = self._original_print
            self._original_print = None

    def action_go_back(self) -> None:
        """Pop the current screen (bound to Escape)."""
        if len(self.screen_stack) > 1:
            self.pop_screen()

    def add_log_line(self, text: str, level: str = "INFO") -> None:
        """Write a line to the active LogViewer widget.

        Called from worker threads via call_from_thread, and also directly
        from the async loop for captured print() output.
        """
        try:
            from graphqler.tui.widgets.log_viewer import LogViewer

            viewer = self.screen.query_one(LogViewer)
            viewer.write_line(text, level)
        except Exception:
            pass
