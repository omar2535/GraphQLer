"""Fuzz screen — runs the fuzzer with live stats and log output.

Supports three modes:
- ``fuzz``  — run pre-compiled chains against the API
- ``run``   — compile then fuzz in one step
- ``idor``  — run IDOR chains only (requires secondary auth)
"""

import time

from textual import work
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static
from textual.containers import Horizontal, Vertical

from graphqler import config
from graphqler.tui.widgets.log_viewer import LogViewer
from graphqler.tui.widgets.stats_panel import StatsPanel


class FuzzScreen(Screen):
    """Fuzzing screen with live stats, log output, and start/stop controls."""

    BINDINGS = [
        ("ctrl+q", "app.quit", "Quit"),
        ("escape", "app.go_back", "Back"),
    ]

    def __init__(self, mode: str = "fuzz", **kwargs):
        super().__init__(**kwargs)
        self._mode = mode
        self._fuzz_running = False
        self._start_time: float | None = None

    def compose(self) -> ComposeResult:
        mode_label = {"fuzz": "Fuzz", "run": "Run (Compile + Fuzz)", "idor": "IDOR Fuzz"}.get(self._mode, self._mode.title())
        yield Header()
        with Vertical():
            with Vertical(classes="run-controls"):
                yield Label(f"Mode: {mode_label}", classes="section-header")
                with Horizontal(classes="inline-row"):
                    yield Label("URL", classes="inline-label")
                    yield Input(value=config.TUI_LAST_URL, id="inp-url", placeholder="https://api.example.com/graphql", classes="inline-input")
                with Horizontal(classes="inline-row"):
                    yield Label("Output Path", classes="inline-label")
                    yield Input(value=config.OUTPUT_DIRECTORY, id="inp-path", placeholder="graphqler-output", classes="inline-input")
                with Horizontal(classes="inline-row"):
                    yield Button("▶  Start", id="btn-start", variant="success")
                    yield Button("✕  Back", id="btn-back", variant="default")
                yield Static("", id="fuzz-status", classes="status-label")
            yield StatsPanel(id="fuzz-stats")
            yield LogViewer(id="fuzz-log")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self._tick_stats)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-start":
            self._start_fuzz()

    def _start_fuzz(self) -> None:
        url = self.query_one("#inp-url", Input).value.strip()
        path = self.query_one("#inp-path", Input).value.strip() or config.OUTPUT_DIRECTORY

        if not url:
            self._set_status("URL is required.", error=True)
            return

        config.TUI_LAST_URL = url
        config.OUTPUT_DIRECTORY = path

        self._start_time = time.time()
        self._fuzz_running = True
        self._set_status("Running…")
        self.query_one("#btn-start", Button).disabled = True
        self.query_one("LogViewer", LogViewer).clear()
        self._run_fuzz(self._mode, url, path)

    @work(thread=True)
    def _run_fuzz(self, mode: str, url: str, path: str) -> None:
        """Blocking fuzz work — runs in a background thread.

        Forces DEBUG=True so the fuzzer uses threading (not multiprocessing),
        which allows the on_chain_start/on_chain_done callbacks and the logging
        bridge to work correctly inside the TUI.
        """
        from graphqler.compiler.compiler import Compiler
        from graphqler.fuzzer import Fuzzer
        from graphqler.graph import GraphGenerator
        from graphqler.utils.file_utils import get_or_create_directory
        from graphqler.utils.stats import Stats

        config.DEBUG = config.TUI_MODE  # force threading so callbacks work
        try:
            get_or_create_directory(path)
            stats = Stats()
            stats.set_file_paths(path)

            if mode in ("run", "compile"):
                compiler = Compiler(path, url)
                compiler.run()
                graph_gen = GraphGenerator(path)
                graph_gen.draw_dependency_graph()
                compiler.run_chain_generation_and_save()

            fuzzer = Fuzzer(path, url)

            if mode == "idor":
                fuzzer.run_idor_only()
            else:
                fuzzer.run()

            self.app.call_from_thread(self._on_done, True, "Fuzzing complete ✓")
        except Exception as exc:
            self.app.call_from_thread(self._on_done, False, str(exc))
        finally:
            self._fuzz_running = False

    def _tick_stats(self) -> None:
        """Called every second to refresh the stats panel."""
        if not self._fuzz_running:
            return
        try:
            from graphqler.utils.stats import Stats

            stats = Stats()
            panel = self.query_one("#fuzz-stats", StatsPanel)
            panel.update_from_stats(stats, self._start_time)
        except Exception:
            pass

    def _on_done(self, success: bool, message: str) -> None:
        self._fuzz_running = False
        self._set_status(message, error=not success)
        try:
            self.query_one("#btn-start", Button).disabled = False
            # Final stats refresh
            from graphqler.utils.stats import Stats

            panel = self.query_one("#fuzz-stats", StatsPanel)
            panel.update_from_stats(Stats(), self._start_time)
        except Exception:
            pass

    def _set_status(self, message: str, error: bool = False) -> None:
        try:
            widget = self.query_one("#fuzz-status", Static)
            cls = "bold red" if error else "bold green"
            widget.update(f"[{cls}]{message}[/{cls}]")
        except Exception:
            pass
