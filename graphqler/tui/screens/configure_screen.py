"""Configure screen — form for all GraphQLer settings.

Settings are read from the current ``config`` module values, shown in a
scrollable form, and written back to both the live ``config`` module and to
``<output_path>/config.toml`` on save.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Rule, Static, Switch
from textual.containers import Horizontal, ScrollableContainer

from graphqler import config
from graphqler.utils.config_handler import set_config

# ── Form field maps ────────────────────────────────────────────────────────────
# Each entry drives both value reading in _save() and removes per-field code.
#
# _INPUT_MAP  : (widget_id, config_key, coerce)
#   coerce is a callable applied to the stripped string value; returning None
#   means "leave as None / empty string maps to None".
#
# _SWITCH_MAP : (widget_id, config_key, invert)
#   invert=True means the switch is labelled as the opposite of the config flag
#   (e.g. "Enable Subscriptions" maps to SKIP_SUBSCRIPTIONS = not switch.value)

def _str_or_none(v: str):
    return v or None

def _try_int(v: str):
    try:
        return int(v)
    except ValueError:
        return None

def _try_float(v: str):
    try:
        return float(v)
    except ValueError:
        return None

_INPUT_MAP: tuple[tuple, ...] = (
    # (widget_id,        config_key,               coerce_fn)
    ("inp-path",         "OUTPUT_DIRECTORY",        str),
    ("inp-auth",         "AUTHORIZATION",           _str_or_none),
    ("inp-idor-auth",    "IDOR_SECONDARY_AUTH",     _str_or_none),
    ("inp-proxy",        "PROXY",                   _str_or_none),
    ("inp-timeout",      "REQUEST_TIMEOUT",         _try_int),
    ("inp-rate",         "TIME_BETWEEN_REQUESTS",   _try_float),
    ("inp-max-iter",     "MAX_FUZZING_ITERATIONS",  _try_int),
    ("inp-max-time",     "MAX_TIME",                _try_int),
    ("inp-llm-model",    "LLM_MODEL",               str),
    ("inp-llm-key",      "LLM_API_KEY",             str),
    ("inp-llm-url",      "LLM_BASE_URL",            str),
)

_SWITCH_MAP: tuple[tuple, ...] = (
    # (widget_id,              config_key,                  invert)
    ("sw-disable-mutations",   "DISABLE_MUTATIONS",         False),
    ("sw-allow-deletion",      "ALLOW_DELETION_OF_OBJECTS", False),
    ("sw-subscriptions",       "SKIP_SUBSCRIPTIONS",        True),   # UI says "Enable", config says "Skip"
    ("sw-skip-dos",            "SKIP_DOS_ATTACKS",          False),
    ("sw-skip-injection",      "SKIP_INJECTION_ATTACKS",    False),
    ("sw-use-llm",             "USE_LLM",                   False),
    ("sw-llm-report",          "LLM_ENABLE_REPORTER",       False),
)


class ConfigureScreen(Screen):
    """Scrollable settings form for the GraphQLer TUI."""

    BINDINGS = [
        ("ctrl+q", "app.quit", "Quit"),
        ("escape", "app.go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer(id="configure-scroll"):
            # ── Endpoint ────────────────────────────────────────────────────
            yield Label("Endpoint", classes="section-header")
            yield Rule()
            yield Label("GraphQL URL", classes="field-label")
            yield Input(value=config.TUI_LAST_URL, id="inp-url", placeholder="https://api.example.com/graphql")
            yield Label("Output Path", classes="field-label")
            yield Input(value=config.OUTPUT_DIRECTORY, id="inp-path", placeholder="graphqler-output")

            # ── Authentication ───────────────────────────────────────────────
            yield Label("Authentication", classes="section-header")
            yield Rule()
            yield Label("Primary Auth Token  (e.g. Bearer token123)", classes="field-label")
            yield Input(value=config.AUTHORIZATION or "", id="inp-auth", placeholder="Bearer …", password=True)
            yield Label("IDOR Secondary Auth Token  (attacker token)", classes="field-label")
            yield Input(value=config.IDOR_SECONDARY_AUTH or "", id="inp-idor-auth", placeholder="Bearer …", password=True)

            # ── Network ──────────────────────────────────────────────────────
            yield Label("Network", classes="section-header")
            yield Rule()
            yield Label("Proxy  (e.g. http://127.0.0.1:8080)", classes="field-label")
            yield Input(value=config.PROXY or "", id="inp-proxy", placeholder="http://…")
            yield Label("Request Timeout (seconds)", classes="field-label")
            yield Input(value=str(config.REQUEST_TIMEOUT), id="inp-timeout", placeholder="120")
            yield Label("Delay Between Requests (seconds)", classes="field-label")
            yield Input(value=str(config.TIME_BETWEEN_REQUESTS), id="inp-rate", placeholder="0.001")

            # ── Fuzzing options ──────────────────────────────────────────────
            yield Label("Fuzzing Options", classes="section-header")
            yield Rule()
            yield Label("Max Fuzzing Iterations", classes="field-label")
            yield Input(value=str(config.MAX_FUZZING_ITERATIONS), id="inp-max-iter", placeholder="1")
            yield Label("Max Run Time (seconds)", classes="field-label")
            yield Input(value=str(config.MAX_TIME), id="inp-max-time", placeholder="3600")
            with Horizontal(classes="switch-row"):
                yield Label("Disable Mutations (Query-only mode)", classes="switch-label")
                yield Switch(value=config.DISABLE_MUTATIONS, id="sw-disable-mutations")
            with Horizontal(classes="switch-row"):
                yield Label("Allow Deletion of Objects from Bucket", classes="switch-label")
                yield Switch(value=config.ALLOW_DELETION_OF_OBJECTS, id="sw-allow-deletion")
            with Horizontal(classes="switch-row"):
                yield Label("Enable Subscription Fuzzing (WebSocket)", classes="switch-label")
                yield Switch(value=not config.SKIP_SUBSCRIPTIONS, id="sw-subscriptions")
            with Horizontal(classes="switch-row"):
                yield Label("Skip DoS Attack Payloads", classes="switch-label")
                yield Switch(value=config.SKIP_DOS_ATTACKS, id="sw-skip-dos")
            with Horizontal(classes="switch-row"):
                yield Label("Skip Injection Attack Payloads", classes="switch-label")
                yield Switch(value=config.SKIP_INJECTION_ATTACKS, id="sw-skip-injection")

            # ── LLM (optional) ───────────────────────────────────────────────
            yield Label("LLM Integration (Optional)", classes="section-header")
            yield Rule()
            with Horizontal(classes="switch-row"):
                yield Label("Enable LLM-powered features", classes="switch-label")
                yield Switch(value=config.USE_LLM, id="sw-use-llm")
            yield Label("Model  (litellm format, e.g. gpt-4o-mini)", classes="field-label")
            yield Input(value=config.LLM_MODEL, id="inp-llm-model", placeholder="gpt-4o-mini")
            yield Label("API Key", classes="field-label")
            yield Input(value=config.LLM_API_KEY, id="inp-llm-key", placeholder="sk-…", password=True)
            yield Label("Base URL  (for Ollama / custom proxies)", classes="field-label")
            yield Input(value=config.LLM_BASE_URL, id="inp-llm-url", placeholder="http://localhost:11434")
            with Horizontal(classes="switch-row"):
                yield Label("Generate LLM Vulnerability Report", classes="switch-label")
                yield Switch(value=config.LLM_ENABLE_REPORTER, id="sw-llm-report")

        # Fixed action bar — always visible outside the scroll area
        with Horizontal(id="configure-actions"):
            yield Static("", id="save-status")
            yield Button("Discard", id="btn-cancel", variant="default")
            yield Button("Save Settings", id="btn-save", variant="primary")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.app.pop_screen()
        elif event.button.id == "btn-save":
            self._save()

    def _save(self) -> None:
        """Apply form values to config module and persist to config.toml."""
        try:
            new_cfg: dict = {}

            # Text inputs — read, strip, coerce, skip if coerce returns None
            for widget_id, config_key, coerce in _INPUT_MAP:
                raw = self.query_one(f"#{widget_id}", Input).value.strip()
                value = coerce(raw)
                if value is not None or coerce is _str_or_none:
                    new_cfg[config_key] = value

            # Switches — read bool, optionally invert
            for widget_id, config_key, invert in _SWITCH_MAP:
                value = self.query_one(f"#{widget_id}", Switch).value
                new_cfg[config_key] = (not value) if invert else value

        except Exception as exc:
            self._set_status(f"Error reading form: {exc}", error=True)
            return

        set_config(new_cfg)
        config.TUI_LAST_URL = self.query_one("#inp-url", Input).value.strip()

        # Persist to disk
        try:
            import os

            path = new_cfg.get("OUTPUT_DIRECTORY", config.OUTPUT_DIRECTORY)
            os.makedirs(path, exist_ok=True)
            config_path = f"{path}/{config.CONFIG_FILE_NAME}"
            from graphqler.utils.config_handler import write_config_to_toml

            write_config_to_toml(config_path)
            self._set_status(f"Saved to {config_path}", error=False)
        except Exception as exc:
            self._set_status(f"Saved to memory (could not write file: {exc})", error=True)

    def _set_status(self, message: str, error: bool = False) -> None:
        try:
            widget = self.query_one("#save-status", Static)
            style = "bold red" if error else "bold green"
            widget.update(f"[{style}]{message}[/{style}]")
        except Exception:
            pass
