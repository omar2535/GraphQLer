"""Compile screen — runs the GraphQLer compilation pipeline with live log output."""

from textual import work
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, RadioButton, RadioSet, Static
from textual.containers import Horizontal, Vertical

from graphqler import config
from graphqler.tui.widgets.log_viewer import LogViewer


class CompileScreen(Screen):
    """Compilation screen with mode selector, URL/path inputs and live log."""

    BINDINGS = [
        ("ctrl+q", "app.quit", "Quit"),
        ("escape", "app.go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            with Vertical(classes="run-controls"):
                yield Label("Compile Mode", classes="field-label")
                with RadioSet(id="compile-mode"):
                    yield RadioButton("compile  (full: graph + chains)", id="rb-compile", value=True)
                    yield RadioButton("compile-graph  (introspection + graph only)", id="rb-compile-graph")
                    yield RadioButton("compile-chains  (regenerate chains from existing graph)", id="rb-compile-chains")
                with Horizontal(classes="inline-row"):
                    yield Label("URL", classes="inline-label")
                    yield Input(value=config.TUI_LAST_URL, id="inp-url", placeholder="https://api.example.com/graphql", classes="inline-input")
                with Horizontal(classes="inline-row"):
                    yield Label("Output Path", classes="inline-label")
                    yield Input(value=config.OUTPUT_DIRECTORY, id="inp-path", placeholder="graphqler-output", classes="inline-input")
                with Horizontal(classes="inline-row"):
                    yield Button("▶  Start Compile", id="btn-start", variant="success")
                    yield Button("✕  Back", id="btn-back", variant="default")
                yield Static("", id="compile-status", classes="status-label")
            yield LogViewer(id="compile-log")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-start":
            self._start_compile()

    def _start_compile(self) -> None:
        url = self.query_one("#inp-url", Input).value.strip()
        path = self.query_one("#inp-path", Input).value.strip() or config.OUTPUT_DIRECTORY

        mode_set = self.query_one("#compile-mode", RadioSet)
        selected = mode_set.pressed_button
        if selected is None:
            self._set_status("Please select a compile mode.", error=True)
            return
        mode = selected.id.replace("rb-", "").replace("-", "-")  # maps directly: rb-compile → compile

        if mode != "compile-chains" and not url:
            self._set_status("URL is required for this mode.", error=True)
            return

        # Save URL to config for other screens to reuse
        config.TUI_LAST_URL = url
        config.OUTPUT_DIRECTORY = path

        self._set_status("Running…")
        self.query_one("#btn-start", Button).disabled = True
        self.query_one("LogViewer", LogViewer).clear()
        self._run_compile(mode, url, path)

    @work(thread=True)
    def _run_compile(self, mode: str, url: str, path: str) -> None:
        """Blocking compilation work — runs in a background thread."""
        from graphqler.compiler.compiler import Compiler
        from graphqler.graph import GraphGenerator
        from graphqler.utils.file_utils import get_or_create_directory

        try:
            get_or_create_directory(path)
            compiler = Compiler(path, url)

            if mode in ("compile", "compile-graph"):
                compiler.run()
                graph_gen = GraphGenerator(path)
                graph = graph_gen.get_dependency_graph()
                graph_gen.draw_dependency_graph()
                node_count = len(graph.nodes)
                edge_count = len(graph.edges)
                self.app.call_from_thread(
                    self._set_status,
                    f"Graph built: {node_count} nodes, {edge_count} edges",
                )

            if mode in ("compile", "compile-chains"):
                compiler.run_chain_generation_and_save()

            self.app.call_from_thread(self._on_done, True, "Compilation complete ✓")
        except Exception as exc:
            self.app.call_from_thread(self._on_done, False, str(exc))

    def _on_done(self, success: bool, message: str) -> None:
        self._set_status(message, error=not success)
        try:
            self.query_one("#btn-start", Button).disabled = False
        except Exception:
            pass

    def _set_status(self, message: str, error: bool = False) -> None:
        try:
            widget = self.query_one("#compile-status", Static)
            cls = "bold red" if error else "bold green"
            widget.update(f"[{cls}]{message}[/{cls}]")
        except Exception:
            pass
