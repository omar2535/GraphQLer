"""Unit tests for GraphQLer TUI components.

Uses Textual's Pilot testing framework to verify that screens mount without
errors and that key interactions work correctly.
"""

import pytest

from graphqler.tui.app import GraphQLerApp


@pytest.mark.anyio
async def test_app_mounts_home_screen():
    """The TUI app should open and show the HomeScreen."""
    app = GraphQLerApp(splash=False)
    async with app.run_test():
        from graphqler.tui.screens.home_screen import HomeScreen

        assert isinstance(app.screen, HomeScreen)


@pytest.mark.anyio
async def test_home_screen_has_mode_buttons():
    """HomeScreen should render all 6 mode buttons."""
    app = GraphQLerApp(splash=False)
    async with app.run_test():
        button_ids = {btn.id for btn in app.screen.query("Button")}
        assert "btn-compile" in button_ids
        assert "btn-fuzz" in button_ids
        assert "btn-run" in button_ids
        assert "btn-idor" in button_ids
        assert "btn-chains" in button_ids
        assert "btn-query" in button_ids
        assert "btn-configure" in button_ids


@pytest.mark.anyio
async def test_navigate_to_configure_screen():
    """Pressing the Configure button should push the ConfigureScreen."""
    app = GraphQLerApp(splash=False)
    async with app.run_test() as pilot:
        await pilot.click("#btn-configure")
        from graphqler.tui.screens.configure_screen import ConfigureScreen

        assert isinstance(app.screen, ConfigureScreen)


@pytest.mark.anyio
async def test_navigate_back_from_configure():
    """Pressing Escape from ConfigureScreen should return to HomeScreen."""
    app = GraphQLerApp(splash=False)
    async with app.run_test() as pilot:
        await pilot.click("#btn-configure")
        await pilot.press("escape")
        from graphqler.tui.screens.home_screen import HomeScreen

        assert isinstance(app.screen, HomeScreen)


@pytest.mark.anyio
async def test_navigate_to_compile_screen():
    """Pressing the Compile button should push the CompileScreen."""
    app = GraphQLerApp(splash=False)
    async with app.run_test() as pilot:
        await pilot.click("#btn-compile")
        from graphqler.tui.screens.compile_screen import CompileScreen

        assert isinstance(app.screen, CompileScreen)


@pytest.mark.anyio
async def test_navigate_to_fuzz_screen():
    """Pressing the Fuzz button should push the FuzzScreen in fuzz mode."""
    app = GraphQLerApp(splash=False)
    async with app.run_test() as pilot:
        await pilot.click("#btn-fuzz")
        from graphqler.tui.screens.fuzz_screen import FuzzScreen

        assert isinstance(app.screen, FuzzScreen)
        assert app.screen._mode == "fuzz"


@pytest.mark.anyio
async def test_navigate_to_chain_explorer():
    """Pressing the Chain Explorer button should push the ChainExplorerScreen."""
    app = GraphQLerApp(splash=False)
    async with app.run_test() as pilot:
        await pilot.click("#btn-chains")
        from graphqler.tui.screens.chain_explorer_screen import ChainExplorerScreen

        assert isinstance(app.screen, ChainExplorerScreen)


@pytest.mark.anyio
async def test_navigate_to_query_editor():
    """Pressing the Query Editor button should push the QueryEditorScreen."""
    app = GraphQLerApp(splash=False)
    async with app.run_test() as pilot:
        await pilot.click("#btn-query")
        from graphqler.tui.screens.query_editor_screen import QueryEditorScreen

        assert isinstance(app.screen, QueryEditorScreen)


@pytest.mark.anyio
async def test_configure_screen_has_url_input():
    """ConfigureScreen should render a URL input field."""
    app = GraphQLerApp(splash=False)
    async with app.run_test() as pilot:
        await pilot.click("#btn-configure")
        await pilot.pause()
        from textual.widgets import Input

        assert app.screen.query_one("#inp-url", Input) is not None


@pytest.mark.anyio
async def test_configure_save_updates_config():
    """Saving the configure form should update the live config."""
    from graphqler import config

    app = GraphQLerApp(splash=False)
    async with app.run_test() as pilot:
        await pilot.click("#btn-configure")
        await pilot.pause()
        from textual.widgets import Input
        from graphqler.tui.screens.configure_screen import ConfigureScreen

        configure_screen = app.screen
        assert isinstance(configure_screen, ConfigureScreen)
        inp = configure_screen.query_one("#inp-url", Input)
        inp.value = "https://test.example.com/graphql"
        configure_screen._save()
        assert config.TUI_LAST_URL == "https://test.example.com/graphql"


@pytest.mark.anyio
async def test_arrow_key_navigation():
    """Arrow keys should move focus between the 6 mode buttons on HomeScreen."""
    app = GraphQLerApp(splash=False)
    async with app.run_test() as pilot:
        # After mount, btn-compile should be focused
        assert app.focused is not None
        assert app.focused.id == "btn-compile"

        # Right → btn-fuzz
        await pilot.press("right")
        assert app.focused.id == "btn-fuzz"

        # Right → btn-run
        await pilot.press("right")
        assert app.focused.id == "btn-run"

        # Down → btn-query (same column, row below)
        await pilot.press("down")
        assert app.focused.id == "btn-query"

        # Left → btn-chains
        await pilot.press("left")
        assert app.focused.id == "btn-chains"


@pytest.mark.anyio
async def test_navigate_to_file_browser():
    """Pressing Browse Output button should push the FileBrowserScreen."""
    app = GraphQLerApp(splash=False)
    async with app.run_test() as pilot:
        await pilot.click("#btn-browse")
        from graphqler.tui.screens.file_browser_screen import FileBrowserScreen

        assert isinstance(app.screen, FileBrowserScreen)


@pytest.mark.anyio
async def test_splash_screen_mounts():
    """SplashScreen should mount and reveal logo lines."""
    from graphqler.tui.screens.splash_screen import SplashScreen

    app = GraphQLerApp(splash=False)
    async with app.run_test() as pilot:
        app.push_screen(SplashScreen())
        await pilot.pause(delay=0.8)
        assert isinstance(app.screen, SplashScreen)
        from textual.widgets import Static

        logo = app.screen.query_one("#splash-logo", Static)
        rendered = str(logo.render())
        assert len(rendered) > 0


@pytest.mark.anyio
async def test_splash_screen_dismisses_on_keypress():
    """Pressing any key on SplashScreen should dismiss it back to HomeScreen."""
    from graphqler.tui.screens.home_screen import HomeScreen
    from graphqler.tui.screens.splash_screen import SplashScreen

    app = GraphQLerApp(splash=False)
    async with app.run_test() as pilot:
        app.push_screen(SplashScreen())
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()
        assert isinstance(app.screen, HomeScreen)
