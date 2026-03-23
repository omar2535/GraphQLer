"""Chain Explorer screen — browse, inspect, and execute individual saved chains."""

from textual import work
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, RichLog, Static
from textual.containers import Horizontal, Vertical

from graphqler import config
from graphqler.tui.widgets.chain_list import ChainList


class ChainExplorerScreen(Screen):
    """Browse compiled chains and execute them individually against the target API."""

    BINDINGS = [
        ("ctrl+q", "app.quit", "Quit"),
        ("escape", "app.go_back", "Back"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._chains: list = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            # Top controls bar
            with Horizontal(classes="run-controls"):
                with Horizontal(classes="inline-row"):
                    yield Label("Output Path", classes="inline-label")
                    yield Input(value=config.OUTPUT_DIRECTORY, id="inp-path", placeholder="graphqler-output", classes="inline-input")
                with Horizontal(classes="inline-row"):
                    yield Label("URL", classes="inline-label")
                    yield Input(value=config.TUI_LAST_URL, id="inp-url", placeholder="https://api.example.com/graphql", classes="inline-input")
                with Horizontal(classes="inline-row"):
                    yield Button("↺  Load Chains", id="btn-load", variant="primary")
                    yield Button("▶  Execute Selected Chain", id="btn-execute", variant="success")
                    yield Button("✕  Back", id="btn-back", variant="default")
                yield Static("", id="explorer-status", classes="status-label")

            # Chain browser + detail
            with Horizontal(id="chain-browser"):
                with Vertical(id="chain-list-panel"):
                    yield Label("Chains", classes="section-header")
                    yield ChainList(id="chain-list")
                with Vertical(id="chain-detail-panel"):
                    yield Label("Steps", classes="section-header")
                    yield RichLog(id="steps-log", markup=True, wrap=True)

            # Response output
            with Vertical(id="chain-response-panel"):
                yield Label("Execution Output", classes="section-header")
                yield RichLog(id="response-log", markup=True, wrap=True)

        yield Footer()

    def on_mount(self) -> None:
        self._load_chains(config.OUTPUT_DIRECTORY)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-load":
            path = self.query_one("#inp-path", Input).value.strip() or config.OUTPUT_DIRECTORY
            self._load_chains(path)
        elif event.button.id == "btn-execute":
            self._execute_selected()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Show steps for the highlighted chain row."""
        try:
            idx = event.cursor_row
            if 0 <= idx < len(self._chains):
                self._show_steps(self._chains[idx])
        except Exception:
            pass

    def _load_chains(self, path: str) -> None:
        from graphqler.chains import ChainGenerator
        from graphqler.graph import GraphGenerator

        config.OUTPUT_DIRECTORY = path
        try:
            graph = GraphGenerator(path).get_dependency_graph()
            self._chains = ChainGenerator().load_from_yaml(path, graph)
            chain_list = self.query_one("#chain-list", ChainList)
            chain_list.load_chains(self._chains)
            self._set_status(f"Loaded {len(self._chains)} chain(s) from {path}")
            if self._chains:
                self._show_steps(self._chains[0])
        except Exception as exc:
            self._set_status(f"Could not load chains: {exc}  (run Compile first)", error=True)

    def _show_steps(self, chain) -> None:
        """Populate the steps panel with the chain's steps."""
        try:
            log = self.query_one("#steps-log", RichLog)
            log.clear()
            log.write(f"[bold]{chain.name or 'unnamed'}[/bold]  [{chain.confidence:.2f} confidence]")
            log.write(f"[dim]{chain.reason or ''}[/dim]")
            log.write("")
            for i, step in enumerate(chain.steps, 1):
                profile_color = "cyan" if step.profile_name == "primary" else "yellow"
                log.write(f"  {i}. [bold]{step.node.name}[/bold]  [[{profile_color}]{step.profile_name}[/{profile_color}]]  ({step.node.graphql_type})")
        except Exception:
            pass

    def _execute_selected(self) -> None:
        url = self.query_one("#inp-url", Input).value.strip()
        path = self.query_one("#inp-path", Input).value.strip() or config.OUTPUT_DIRECTORY

        if not url:
            self._set_status("URL is required to execute a chain.", error=True)
            return

        chain_list = self.query_one("#chain-list", ChainList)
        idx = chain_list.get_selected_index()
        if idx is None or idx < 0 or idx >= len(self._chains):
            self._set_status("Select a chain from the list first.", error=True)
            return

        selected_chain = self._chains[idx]
        config.TUI_LAST_URL = url
        config.OUTPUT_DIRECTORY = path
        config.DEBUG = True  # force threading for callbacks

        self._set_status(f"Executing chain: {selected_chain.name or f'chain-{idx}'}…")
        try:
            self.query_one("#response-log", RichLog).clear()
        except Exception:
            pass
        self._run_chain(selected_chain, url, path)

    @work(thread=True)
    def _run_chain(self, chain, url: str, path: str) -> None:
        """Execute a single chain in a background thread."""
        from graphqler.fuzzer import Fuzzer
        from graphqler.utils.file_utils import get_or_create_directory

        try:
            get_or_create_directory(path)
            fuzzer = Fuzzer(path, url)
            fuzzer.run_chain(chain)
            self.app.call_from_thread(self._on_chain_done, True, "Chain executed ✓")
        except Exception as exc:
            self.app.call_from_thread(self._on_chain_done, False, str(exc))

    def _on_chain_done(self, success: bool, message: str) -> None:
        self._set_status(message, error=not success)
        try:
            log = self.query_one("#response-log", RichLog)
            cls = "green" if success else "red"
            log.write(f"[{cls}]{message}[/{cls}]")
        except Exception:
            pass

    def _set_status(self, message: str, error: bool = False) -> None:
        try:
            widget = self.query_one("#explorer-status", Static)
            cls = "bold red" if error else "bold green"
            widget.update(f"[{cls}]{message}[/{cls}]")
        except Exception:
            pass
