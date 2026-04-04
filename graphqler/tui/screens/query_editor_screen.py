"""Query Editor screen — compose and send individual GraphQL requests."""

import json

from textual import work
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, RichLog, Static, TextArea
from textual.containers import Horizontal, Vertical

from graphqler import config


_DEFAULT_QUERY = """{
  __schema {
    queryType { name }
    mutationType { name }
  }
}"""


class QueryEditorScreen(Screen):
    """Free-form GraphQL query editor with response display."""

    BINDINGS = [
        ("ctrl+q", "app.quit", "Quit"),
        ("escape", "app.go_back", "Back"),
        ("ctrl+enter", "send", "Send"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            # ── Top controls ─────────────────────────────────────────────────
            with Vertical(id="query-top"):
                with Horizontal(classes="inline-row"):
                    yield Label("URL", classes="inline-label")
                    yield Input(value=config.TUI_LAST_URL, id="inp-url", placeholder="https://api.example.com/graphql", classes="inline-input")
                with Horizontal(classes="inline-row"):
                    yield Label("Auth Token", classes="inline-label")
                    yield Input(value=config.AUTHORIZATION or "", id="inp-auth", placeholder="Bearer …", classes="inline-input")
                with Horizontal(classes="inline-row"):
                    yield Button("▶  Send  (Ctrl+Enter)", id="btn-send", variant="success")
                    yield Button("⌫  Clear", id="btn-clear", variant="default")
                    yield Button("✕  Back", id="btn-back", variant="default")
                yield Static("", id="query-status", classes="status-label")

            # ── Query + Variables | Response ─────────────────────────────────
            with Horizontal(id="query-body"):
                with Vertical(id="query-left"):
                    yield Label("Query / Mutation", classes="field-label")
                    yield TextArea.code_editor(_DEFAULT_QUERY, language="graphql", id="query-editor")
                    yield Label("Variables (JSON)", classes="field-label")
                    yield TextArea.code_editor("{}", language="json", id="variables-editor")
                with Vertical(id="query-right"):
                    yield Label("Response", classes="field-label")
                    yield RichLog(id="response-display", markup=True, wrap=False, highlight=True)

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-send":
            self.action_send()
        elif event.button.id == "btn-clear":
            self._clear()

    def action_send(self) -> None:
        """Send the current query to the endpoint."""
        url = self.query_one("#inp-url", Input).value.strip()
        if not url:
            self._set_status("URL is required.", error=True)
            return

        auth = self.query_one("#inp-auth", Input).value.strip()
        query_text = self.query_one("#query-editor", TextArea).text.strip()
        variables_text = self.query_one("#variables-editor", TextArea).text.strip()

        if not query_text:
            self._set_status("Query cannot be empty.", error=True)
            return

        try:
            variables = json.loads(variables_text) if variables_text and variables_text != "{}" else {}
        except json.JSONDecodeError as exc:
            self._set_status(f"Variables JSON error: {exc}", error=True)
            return

        config.TUI_LAST_URL = url
        self._set_status("Sending…")
        self.query_one("#btn-send", Button).disabled = True
        self.query_one("#response-display", RichLog).clear()
        self._send_request(url, auth, query_text, variables)

    @work(thread=True)
    def _send_request(self, url: str, auth: str, query: str, variables: dict) -> None:
        """Send the GraphQL request in a background thread."""
        import requests as _requests

        from graphqler.utils.request_utils import get_proxies

        try:
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            if auth:
                headers["Authorization"] = auth

            body: dict = {"query": query}
            if variables:
                body["variables"] = variables

            proxies = get_proxies()
            response = _requests.post(url, json=body, headers=headers, timeout=config.REQUEST_TIMEOUT, proxies=proxies)

            try:
                gql_response = response.json()
                formatted = json.dumps(gql_response, indent=2)
            except Exception:
                formatted = response.text

            self.app.call_from_thread(self._show_response, response.status_code, formatted, success=response.ok)
        except Exception as exc:
            self.app.call_from_thread(self._show_response, 0, str(exc), success=False)

    def _show_response(self, status_code: int, body: str, success: bool = True) -> None:
        status_color = "green" if success else "red"
        status_label = f"HTTP {status_code}" if status_code else "Error"
        self._set_status(f"[{status_color}]{status_label}[/{status_color}]")

        try:
            log = self.query_one("#response-display", RichLog)
            log.write(f"[{status_color}]─── {status_label} ───[/{status_color}]")
            # Write the body in chunks to avoid very large single writes
            for line in body.splitlines():
                log.write(line)
        except Exception:
            pass

        try:
            self.query_one("#btn-send", Button).disabled = False
        except Exception:
            pass

    def _clear(self) -> None:
        try:
            self.query_one("#query-editor", TextArea).clear()
            self.query_one("#variables-editor", TextArea).load_text("{}")
            self.query_one("#response-display", RichLog).clear()
            self._set_status("")
        except Exception:
            pass

    def _set_status(self, message: str, error: bool = False) -> None:
        try:
            widget = self.query_one("#query-status", Static)
            if error:
                widget.update(f"[bold red]{message}[/bold red]")
            else:
                widget.update(message)
        except Exception:
            pass
