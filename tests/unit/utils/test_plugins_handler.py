import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from graphqler.utils import plugins_handler
from graphqler.utils.protocols.request_utils_protocol import RequestUtilsProtocol

@pytest.fixture
def mock_plugin_path():
    return Path(__file__).parent / "mock_plugins"

def test_does_plugin_exist(mock_plugin_path):
    with patch('graphqler.config.PLUGINS_PATH', mock_plugin_path):
        assert plugins_handler.does_plugin_exist("request_utils.py")
        assert not plugins_handler.does_plugin_exist("nonexistent.py")

def test_get_plugin_path():
    plugin_name = "test_plugin.py"
    path = plugins_handler.get_plugin_path(plugin_name)
    assert isinstance(path, Path)
    assert path.name == plugin_name

def test_get_request_utils_with_valid_plugin(mock_plugin_path):
    with patch('graphqler.config.PLUGINS_PATH', mock_plugin_path):
        utils = plugins_handler.get_request_utils()
        assert isinstance(utils, RequestUtilsProtocol)
        # Test actual mock implementation
        response = utils.send_graphql_request("http://example.com", {"query": "test"})
        assert response[0] == {"data": {"message": "Success"}}

def test_get_plugin_fallback_to_default():
    with patch('graphqler.utils.plugins_handler.does_plugin_exist', return_value=False):  # Fixed path
        plugin = plugins_handler.get_plugin("request_utils.py")
        assert plugin == plugins_handler.POSSIBLE_PLUGINS["request_utils.py"]

def test_invalid_plugin_structure():
    with pytest.raises(AssertionError):
        with patch('graphqler.utils.plugins_handler.get_plugin') as mock_get_plugin:  # Fixed path
            mock_get_plugin.return_value = MagicMock(spec=[])  # Empty plugin without required methods
            plugins_handler.get_request_utils()
