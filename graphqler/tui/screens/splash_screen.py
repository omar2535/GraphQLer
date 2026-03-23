"""Animated startup splash screen, shown once per calendar day."""

import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

# The same figlet art used in the README image (standard font)
_LOGO_LINES = [
    r"  ____                 _      ___  _",
    r" / ___|_ __ __ _ _ __ | |__  / _ \| |     ___ _ __",
    r"| |  _| '__/ _` | '_ \| '_ \| | | | |    / _ \ '__|",
    r"| |_| | | | (_| | |_) | | | | |_| | |___|  __/ |",
    r" \____|_|  \__,_| .__/|_| |_|\__\_\_____|\___| |",
    r"                |_|",
]

_TAGLINE = "the dependency-aware graphql api fuzzer"
_PROMPT = "press any key"

_STATE_FILE = Path.home() / ".config" / "graphqler" / ".last_splash"


def should_show_splash() -> bool:
    """Return True if the splash has not been shown today."""
    today = datetime.date.today().isoformat()
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _STATE_FILE.exists() and _STATE_FILE.read_text().strip() == today:
            return False
        _STATE_FILE.write_text(today)
    except Exception:
        pass
    return True


class SplashScreen(Screen):
    """Logo reveal animation — one line per tick, then tagline + prompt."""

    DEFAULT_CSS = """
    SplashScreen {
        align: center middle;
        background: $background;
    }
    #splash-logo {
        text-style: bold;
        color: $accent;
        width: auto;
        height: auto;
        padding: 0 4;
    }
    #splash-tagline {
        color: $text-muted;
        text-style: italic;
        width: 60;
        content-align: center middle;
        height: 2;
        margin-top: 1;
    }
    #splash-prompt {
        color: $text-disabled;
        width: 60;
        content-align: center middle;
        height: 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="splash-logo")
        yield Static("", id="splash-tagline")
        yield Static("", id="splash-prompt")

    def on_mount(self) -> None:
        self._revealed: list[str] = []
        self._next_line = 0
        self._reveal_timer = self.set_interval(0.11, self._tick)

    def _tick(self) -> None:
        if self._next_line < len(_LOGO_LINES):
            self._revealed.append(_LOGO_LINES[self._next_line])
            self._next_line += 1
            self.query_one("#splash-logo", Static).update("\n".join(self._revealed))
        else:
            self._reveal_timer.stop()
            self.set_timer(0.3, self._show_tagline)

    def _show_tagline(self) -> None:
        self.query_one("#splash-tagline", Static).update(_TAGLINE)
        self.set_timer(0.5, self._show_prompt)

    def _show_prompt(self) -> None:
        self.query_one("#splash-prompt", Static).update(_PROMPT)
        self.set_timer(7.0, self._auto_dismiss)

    def _auto_dismiss(self) -> None:
        if self.app.screen is self:
            self.app.pop_screen()

    def on_key(self) -> None:
        self.app.pop_screen()

    def on_click(self) -> None:
        self.app.pop_screen()
