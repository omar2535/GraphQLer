"""File browser screen — explore the GraphQLer output directory.

Shows a DirectoryTree on the left and file content on the right.
Useful for inspecting stats, chain YAMLs, detection results, and logs
without leaving the TUI.
"""

import os
from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, DirectoryTree, Footer, Header, Input, Label, RichLog, Static
from textual.containers import Horizontal, Vertical

from graphqler import config

# Files larger than this are truncated to avoid freezing the UI
_MAX_DISPLAY_BYTES = 256 * 1024  # 256 KB


class FileBrowserScreen(Screen):
    """Browse the output directory and view file contents."""

    BINDINGS = [
        ("ctrl+q", "app.quit", "Quit"),
        ("escape", "app.go_back", "Back"),
        ("r", "reload", "Reload"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            # Top bar
            with Horizontal(classes="run-controls"):
                with Horizontal(classes="inline-row"):
                    yield Label("Output Path", classes="inline-label")
                    yield Input(value=config.OUTPUT_DIRECTORY, id="inp-path", classes="inline-input")
                with Horizontal(classes="inline-row"):
                    yield Button("↺  Reload  (R)", id="btn-reload", variant="primary")
                    yield Button("✕  Back", id="btn-back", variant="default")
                yield Static("", id="browser-status", classes="status-label")

            # Tree + Content
            with Horizontal(id="browser-body"):
                with Vertical(id="browser-tree-panel"):
                    yield Label("Directory Tree", classes="section-header")
                    yield DirectoryTree(config.OUTPUT_DIRECTORY, id="dir-tree")
                with Vertical(id="browser-content-panel"):
                    yield Label("File Content", classes="section-header", id="content-label")
                    yield RichLog(id="file-content", markup=False, wrap=True, highlight=False)

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-reload":
            self.action_reload()

    def action_reload(self) -> None:
        """Reload the directory tree from the current path input."""
        path = self.query_one("#inp-path", Input).value.strip() or config.OUTPUT_DIRECTORY
        self._load_tree(path)

    def _load_tree(self, path: str) -> None:
        if not os.path.isdir(path):
            self._set_status(f"Directory not found: {path}", error=True)
            return
        try:
            tree = self.query_one("#dir-tree", DirectoryTree)
            tree.path = Path(path)
            tree.reload()
            self._set_status(f"Browsing: {path}")
        except Exception as exc:
            self._set_status(f"Error loading tree: {exc}", error=True)

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Display the selected file's contents in the right panel."""
        path: Path = event.path
        self._show_file(path)

    def _show_file(self, path: Path) -> None:
        log = self.query_one("#file-content", RichLog)
        log.clear()

        try:
            size = path.stat().st_size
            truncated = size > _MAX_DISPLAY_BYTES

            content = path.read_bytes()[:_MAX_DISPLAY_BYTES].decode("utf-8", errors="replace")

            # Write header
            log.write(f"── {path} ──")
            log.write(f"Size: {size:,} bytes" + (" (showing first 256 KB)" if truncated else ""))
            log.write("")

            for line in content.splitlines():
                log.write(line)

            if truncated:
                log.write("")
                log.write("… (file truncated)")

            self._set_status(f"{path.name}  ({size:,} bytes)")
            try:
                self.query_one("#content-label", Label).update(f"File Content — {path.name}")
            except Exception:
                pass
        except PermissionError:
            log.write(f"[Permission denied: {path}]")
            self._set_status(f"Permission denied: {path}", error=True)
        except Exception as exc:
            log.write(f"[Error reading file: {exc}]")
            self._set_status(str(exc), error=True)

    def _set_status(self, message: str, error: bool = False) -> None:
        try:
            widget = self.query_one("#browser-status", Static)
            cls = "bold red" if error else "bold green"
            widget.update(f"[{cls}]{message}[/{cls}]")
        except Exception:
            pass
