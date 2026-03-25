"""Home / dashboard screen — the first screen the user sees."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Rule
from textual.containers import Grid, Horizontal, Vertical

from graphqler import config

# Ordered list of button IDs in row-major order for arrow-key navigation
_GRID_BUTTONS = [
    ["btn-compile", "btn-fuzz", "btn-run"],
    ["btn-idor", "btn-chains", "btn-query"],
]


class HomeScreen(Screen):
    """Landing screen with mode selection buttons and a config summary sidebar."""

    BINDINGS = [
        ("ctrl+q", "app.quit", "Quit"),
        ("up", "focus_up", ""),
        ("down", "focus_down", ""),
        ("left", "focus_left", ""),
        ("right", "focus_right", ""),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="home-main"):
                with Grid(id="mode-grid"):
                    yield Button("Compile", id="btn-compile", classes="mode-btn")
                    yield Button("Fuzz", id="btn-fuzz", classes="mode-btn")
                    yield Button("Run", id="btn-run", classes="mode-btn mode-btn--primary")
                    yield Button("IDOR", id="btn-idor", classes="mode-btn")
                    yield Button("Chain Explorer", id="btn-chains", classes="mode-btn")
                    yield Button("Query Editor", id="btn-query", classes="mode-btn")
            with Vertical(id="home-sidebar"):
                yield Label("ENDPOINT", classes="sidebar-section")
                yield Label(config.TUI_LAST_URL or "not configured", id="cfg-url", classes="config-value")
                yield Label("OUTPUT", classes="sidebar-section")
                yield Label(config.OUTPUT_DIRECTORY, id="cfg-path", classes="config-value")
                yield Label("AUTH", classes="sidebar-section")
                yield Label("set" if config.AUTHORIZATION else "\u2014", id="cfg-auth", classes="config-value")
                yield Rule()
                yield Button("Configure", id="btn-configure", variant="default")
                yield Button("Browse Output", id="btn-browse", variant="default")
        yield Footer()

    def on_mount(self) -> None:
        """Focus the first mode button so arrow-key navigation works immediately."""
        self.query_one("#btn-compile", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:  # noqa: C901
        match event.button.id:
            case "btn-compile":
                from graphqler.tui.screens.compile_screen import CompileScreen

                self.app.push_screen(CompileScreen())
            case "btn-fuzz":
                from graphqler.tui.screens.fuzz_screen import FuzzScreen

                self.app.push_screen(FuzzScreen(mode="fuzz"))
            case "btn-run":
                from graphqler.tui.screens.fuzz_screen import FuzzScreen

                self.app.push_screen(FuzzScreen(mode="run"))
            case "btn-idor":
                from graphqler.tui.screens.fuzz_screen import FuzzScreen

                self.app.push_screen(FuzzScreen(mode="idor"))
            case "btn-chains":
                from graphqler.tui.screens.chain_explorer_screen import ChainExplorerScreen

                self.app.push_screen(ChainExplorerScreen())
            case "btn-query":
                from graphqler.tui.screens.query_editor_screen import QueryEditorScreen

                self.app.push_screen(QueryEditorScreen())
            case "btn-configure":
                from graphqler.tui.screens.configure_screen import ConfigureScreen

                self.app.push_screen(ConfigureScreen())
            case "btn-browse":
                from graphqler.tui.screens.file_browser_screen import FileBrowserScreen

                self.app.push_screen(FileBrowserScreen())

    def on_resume(self) -> None:
        """Refresh the config summary whenever we return to this screen."""
        try:
            self.query_one("#cfg-url", Label).update(config.TUI_LAST_URL or "not configured")
            self.query_one("#cfg-path", Label).update(config.OUTPUT_DIRECTORY)
            self.query_one("#cfg-auth", Label).update("set" if config.AUTHORIZATION else "\u2014")
        except Exception:
            pass
        self.query_one("#btn-compile", Button).focus()

    # ── Arrow-key navigation ───────────────────────────────────────────────

    def action_focus_up(self) -> None:
        self._move_grid_focus(-1, 0)

    def action_focus_down(self) -> None:
        self._move_grid_focus(1, 0)

    def action_focus_left(self) -> None:
        self._move_grid_focus(0, -1)

    def action_focus_right(self) -> None:
        self._move_grid_focus(0, 1)

    def _move_grid_focus(self, dr: int, dc: int) -> None:
        """Move grid focus by (row-delta, col-delta), wrapping at edges."""
        focused = self.focused
        current_id = focused.id if focused else None

        for r, row in enumerate(_GRID_BUTTONS):
            if current_id in row:
                c = row.index(current_id)
                nr = (r + dr) % len(_GRID_BUTTONS)
                nc = (c + dc) % len(row)
                self.query_one(f"#{_GRID_BUTTONS[nr][nc]}", Button).focus()
                return

        # Focused widget is outside the grid — jump to first button
        self.query_one("#btn-compile", Button).focus()
