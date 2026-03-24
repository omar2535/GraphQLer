"""Main Textual application entry point for the GraphQLer TUI."""

import builtins
import logging

from textual.app import App


class GraphQLerApp(App):
    """Root Textual application; manages screen navigation and stdout capture."""

    TITLE = "GraphQLer"
    SUB_TITLE = "GraphQL API Fuzzer & Security Testing Tool"
    CSS_PATH = "graphqler.tcss"
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, *args, splash: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_print = None
        self._splash = splash
        self._prev_tui_mode = False
        self._log_handler = None

    def on_mount(self) -> None:
        from graphqler import config as _config
        from graphqler.tui.logging_handler import TUILogHandler
        from graphqler.tui.screens.home_screen import HomeScreen
        from graphqler.tui.screens.splash_screen import SplashScreen, should_show_splash

        self._prev_tui_mode = _config.TUI_MODE
        _config.TUI_MODE = True  # tell the fuzzer to use threads, not multiprocessing

        # Install logging bridge so library log calls appear in the TUI
        self._log_handler = TUILogHandler(self)
        root_logger = logging.getLogger()
        root_logger.addHandler(self._log_handler)

        self._install_print_capture()
        self.push_screen(HomeScreen())
        if self._splash and should_show_splash():
            self.push_screen(SplashScreen())

    def on_unmount(self) -> None:
        from graphqler import config as _config

        _config.TUI_MODE = self._prev_tui_mode

        if self._log_handler is not None:
            logging.getLogger().removeHandler(self._log_handler)
            self._log_handler = None

        self._restore_print()

    def _install_print_capture(self) -> None:
        """Replace builtins.print with a version that forwards to the LogViewer.

        Only plain print() calls (to stdout) are captured; explicit file= writes
        (e.g. print(..., file=sys.stderr)) use the original print unchanged.
        Carriage-return lines (end="\\r") and empty print() calls are forwarded
        to the original so running-stats overwrite behaviour is preserved.
        """
        import sys

        app = self
        self._original_print = builtins.print

        def _tui_print(*args, sep: str = " ", end: str = "\n", file=None, flush: bool = False) -> None:
            if file is not None and file is not sys.stdout:
                app._original_print(*args, sep=sep, end=end, file=file, flush=flush)
                return
            # Carriage-return lines (progress bars, in-place stats) fall through
            # to the real print so they behave correctly if a real terminal is
            # also attached; they are not forwarded to the log widget.
            if end == "\r" or not args:
                app._original_print(*args, sep=sep, end=end, file=sys.stdout, flush=True)
                return
            text = sep.join(str(a) for a in args)
            if text:
                try:
                    app.call_from_thread(app.add_log_line, text, "INFO")
                except Exception:
                    app._original_print(text, end=end, flush=flush)

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
