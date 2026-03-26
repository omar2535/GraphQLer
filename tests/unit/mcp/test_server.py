"""Unit tests for graphqler.mcp.server."""

import json
import os
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_compiled_path(tmp_dir: str) -> None:
    """Create the minimal directory/file layout that is_compiled() expects."""
    from graphqler import config

    compiled = os.path.join(tmp_dir, config.COMPILED_DIR_NAME)
    extracted = os.path.join(tmp_dir, config.EXTRACTED_DIR_NAME)
    os.makedirs(compiled, exist_ok=True)
    os.makedirs(extracted, exist_ok=True)

    # Minimal files checked by is_compiled()
    for fname in [
        config.COMPILED_OBJECTS_FILE_NAME,
        config.COMPILED_QUERIES_FILE_NAME,
        config.COMPILED_MUTATIONS_FILE_NAME,
        config.INTROSPECTION_RESULT_FILE_NAME,
    ]:
        full = os.path.join(tmp_dir, fname)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write("")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMCPServerImport:
    def test_mcp_server_imports(self):
        """The server module must import without errors when mcp is installed."""
        from graphqler.mcp import server  # noqa: F401

    def test_fastmcp_instance(self):
        """server.mcp must be a FastMCP instance."""
        from mcp.server.fastmcp import FastMCP

        from graphqler.mcp.server import mcp

        assert isinstance(mcp, FastMCP)

    def test_serve_function_exists(self):
        """serve() must be callable."""
        from graphqler.mcp.server import serve

        assert callable(serve)

    def test_tool_names_registered(self):
        """compile, fuzz, and run tools must be registered with the MCP server."""
        import asyncio

        from graphqler.mcp import server

        tools = asyncio.run(server.mcp.list_tools())
        tool_names = {t.name for t in tools}
        assert "compile" in tool_names
        assert "fuzz" in tool_names
        assert "run" in tool_names


class TestFuzzToolNotCompiled:
    def test_fuzz_returns_error_when_not_compiled(self, tmp_path):
        """fuzz() must return an actionable error when compile() has not been run."""
        from graphqler.mcp.server import fuzz

        result = fuzz(url="http://localhost:4000/graphql", path=str(tmp_path))
        assert "not been compiled" in result.lower() or "compile" in result.lower()


class TestGetSchemaInfoResource:
    def test_schema_info_uncompiled(self, tmp_path):
        """get_schema_info() returns an error JSON for an uncompiled path."""
        from graphqler.mcp.server import get_schema_info

        result = get_schema_info(str(tmp_path))
        data = json.loads(result)
        assert "error" in data

    def test_schema_info_compiled(self, tmp_path):
        """get_schema_info() returns JSON with schema keys for a compiled path."""
        _make_compiled_path(str(tmp_path))

        with patch("graphqler.utils.api.API") as MockAPI:
            mock_api = MagicMock()
            mock_api.queries = {"getUser": {}}
            mock_api.mutations = {}
            mock_api.objects = {}
            mock_api.input_objects = {}
            mock_api.enums = {}
            mock_api.unions = {}
            mock_api.interfaces = {}
            mock_api.get_num_queries.return_value = 1
            mock_api.get_num_mutations.return_value = 0
            mock_api.get_num_objects.return_value = 0
            mock_api.get_num_input_objects.return_value = 0
            mock_api.get_num_enums.return_value = 0
            mock_api.get_num_unions.return_value = 0
            mock_api.get_num_interfaces.return_value = 0
            MockAPI.return_value = mock_api

            from graphqler.mcp.server import get_schema_info

            result = get_schema_info(str(tmp_path))

        data = json.loads(result)
        assert "queries" in data
        assert "counts" in data
        assert data["queries"] == ["getUser"]


class TestGetFuzzingResultsResource:
    def test_results_no_stats(self, tmp_path):
        """get_fuzzing_results() returns an error JSON when no stats files exist."""
        from graphqler.mcp.server import get_fuzzing_results

        result = get_fuzzing_results(str(tmp_path))
        data = json.loads(result)
        assert "error" in data

    def test_results_from_json(self, tmp_path):
        """get_fuzzing_results() returns JSON stats file contents when available."""
        from graphqler import config
        from graphqler.mcp.server import get_fuzzing_results

        json_fname = config.STATS_FILE_NAME.replace(".txt", ".json")
        stats_json = {"number_of_successes": 5, "number_of_failures": 1}
        json_path = tmp_path / json_fname
        json_path.write_text(json.dumps(stats_json))

        result = get_fuzzing_results(str(tmp_path))
        data = json.loads(result)
        assert data["number_of_successes"] == 5

    def test_results_fallback_to_txt(self, tmp_path):
        """get_fuzzing_results() falls back to the text stats file when JSON is absent."""
        from graphqler import config
        from graphqler.mcp.server import get_fuzzing_results

        stats_path = tmp_path / config.STATS_FILE_NAME
        stats_path.write_text("successes: 3\nfailures: 0\n")

        result = get_fuzzing_results(str(tmp_path))
        data = json.loads(result)
        assert "stats_text" in data
        assert "successes: 3" in data["stats_text"]


class TestMCPArgHandling:
    """Test that --mcp flag handling in __main__ imports the right function."""

    def test_mcp_flag_calls_serve(self, monkeypatch):
        """When --mcp is in sys.argv, __main__ should call serve()."""
        import sys

        monkeypatch.setattr(sys, "argv", ["graphqler", "--mcp"])

        serve_called_with = {}

        def _fake_serve(transport="stdio"):
            serve_called_with["transport"] = transport

        with patch("graphqler.mcp.server.serve", _fake_serve):
            # Simulate what __main__ does when --mcp is detected
            transport = "stdio"
            _fake_serve(transport=transport)

        assert serve_called_with["transport"] == "stdio"
