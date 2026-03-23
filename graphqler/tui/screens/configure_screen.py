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
            url = self.query_one("#inp-url", Input).value.strip()
            path = self.query_one("#inp-path", Input).value.strip() or config.OUTPUT_DIRECTORY
            auth = self.query_one("#inp-auth", Input).value.strip()
            idor_auth = self.query_one("#inp-idor-auth", Input).value.strip()
            proxy = self.query_one("#inp-proxy", Input).value.strip()
            timeout = self.query_one("#inp-timeout", Input).value.strip()
            rate = self.query_one("#inp-rate", Input).value.strip()
            max_iter = self.query_one("#inp-max-iter", Input).value.strip()
            max_time = self.query_one("#inp-max-time", Input).value.strip()
            disable_mutations = self.query_one("#sw-disable-mutations", Switch).value
            allow_deletion = self.query_one("#sw-allow-deletion", Switch).value
            subscriptions_on = self.query_one("#sw-subscriptions", Switch).value
            skip_dos = self.query_one("#sw-skip-dos", Switch).value
            skip_injection = self.query_one("#sw-skip-injection", Switch).value
            use_llm = self.query_one("#sw-use-llm", Switch).value
            llm_model = self.query_one("#inp-llm-model", Input).value.strip()
            llm_key = self.query_one("#inp-llm-key", Input).value.strip()
            llm_url = self.query_one("#inp-llm-url", Input).value.strip()
            llm_report = self.query_one("#sw-llm-report", Switch).value
        except Exception as exc:
            self._set_status(f"Error reading form: {exc}", error=True)
            return

        # Apply to live config
        new_cfg: dict = {
            "OUTPUT_DIRECTORY": path,
            "AUTHORIZATION": auth or None,
            "IDOR_SECONDARY_AUTH": idor_auth or None,
            "PROXY": proxy or None,
            "DISABLE_MUTATIONS": disable_mutations,
            "ALLOW_DELETION_OF_OBJECTS": allow_deletion,
            "SKIP_SUBSCRIPTIONS": not subscriptions_on,
            "SKIP_DOS_ATTACKS": skip_dos,
            "SKIP_INJECTION_ATTACKS": skip_injection,
            "USE_LLM": use_llm,
            "LLM_MODEL": llm_model,
            "LLM_API_KEY": llm_key,
            "LLM_BASE_URL": llm_url,
            "LLM_ENABLE_REPORTER": llm_report,
        }
        try:
            new_cfg["REQUEST_TIMEOUT"] = int(timeout)
        except ValueError:
            pass
        try:
            new_cfg["TIME_BETWEEN_REQUESTS"] = float(rate)
        except ValueError:
            pass
        try:
            new_cfg["MAX_FUZZING_ITERATIONS"] = int(max_iter)
        except ValueError:
            pass
        try:
            new_cfg["MAX_TIME"] = int(max_time)
        except ValueError:
            pass

        set_config(new_cfg)
        config.TUI_LAST_URL = url

        # Persist to disk
        try:
            import os

            os.makedirs(path, exist_ok=True)
            config_path = f"{path}/{config.CONFIG_FILE_NAME}"
            self._write_toml(config_path)
            self._set_status(f"Saved to {config_path}", error=False)
        except Exception as exc:
            self._set_status(f"Saved to memory (could not write file: {exc})", error=True)

    def _write_toml(self, path: str) -> None:
        """Write current config values to a TOML file."""
        lines = [
            "# GraphQLer configuration — generated by TUI\n",
            f'DEBUG = {"true" if config.DEBUG else "false"}\n',
            f'\nOUTPUT_DIRECTORY = "{config.OUTPUT_DIRECTORY}"\n',
            f'\nAUTHORIZATION = "{config.AUTHORIZATION or ""}"\n',
            f'IDOR_SECONDARY_AUTH = "{config.IDOR_SECONDARY_AUTH or ""}"\n',
            f'PROXY = "{config.PROXY or ""}"\n',
            f"\nREQUEST_TIMEOUT = {config.REQUEST_TIMEOUT}\n",
            f"TIME_BETWEEN_REQUESTS = {config.TIME_BETWEEN_REQUESTS}\n",
            f"\nMAX_FUZZING_ITERATIONS = {config.MAX_FUZZING_ITERATIONS}\n",
            f"MAX_TIME = {config.MAX_TIME}\n",
            f"DISABLE_MUTATIONS = {'true' if config.DISABLE_MUTATIONS else 'false'}\n",
            f"ALLOW_DELETION_OF_OBJECTS = {'true' if config.ALLOW_DELETION_OF_OBJECTS else 'false'}\n",
            f"SKIP_SUBSCRIPTIONS = {'true' if config.SKIP_SUBSCRIPTIONS else 'false'}\n",
            f"SKIP_DOS_ATTACKS = {'true' if config.SKIP_DOS_ATTACKS else 'false'}\n",
            f"SKIP_INJECTION_ATTACKS = {'true' if config.SKIP_INJECTION_ATTACKS else 'false'}\n",
            f"SKIP_MISC_ATTACKS = {'true' if config.SKIP_MISC_ATTACKS else 'false'}\n",
            f"\nUSE_LLM = {'true' if config.USE_LLM else 'false'}\n",
            f'LLM_MODEL = "{config.LLM_MODEL}"\n',
            f'LLM_API_KEY = "{config.LLM_API_KEY}"\n',
            f'LLM_BASE_URL = "{config.LLM_BASE_URL}"\n',
            f"LLM_ENABLE_REPORTER = {'true' if config.LLM_ENABLE_REPORTER else 'false'}\n",
            f"LLM_MAX_RETRIES = {config.LLM_MAX_RETRIES}\n",
            "\nUSE_OBJECTS_BUCKET = true\n",
            "USE_DEPENDENCY_GRAPH = true\n",
            "\nSKIP_NODES = []\n",
            "\n[CUSTOM_HEADERS]\n",
            'Accept = "application/json"\n',
        ]
        with open(path, "w") as fh:
            fh.writelines(lines)

    def _set_status(self, message: str, error: bool = False) -> None:
        try:
            widget = self.query_one("#save-status", Static)
            style = "bold red" if error else "bold green"
            widget.update(f"[{style}]{message}[/{style}]")
        except Exception:
            pass
