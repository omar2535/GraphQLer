import importlib
import importlib.util
import inspect
import pathlib

from graphqler import config
from graphqler.utils import request_utils
from graphqler.utils.protocols.request_utils_protocol import RequestUtilsProtocol

# The possible plugins and their map to the original module in GraphQLer
POSSIBLE_PLUGINS = {
    "request_utils.py": request_utils
}


def get_plugin_path(plugin_name: str) -> pathlib.Path:
    """Gets the plugin path

    Args:
        plugin_name (str): The plugin name

    Returns:
        pathlib.Path: The plugin path
    """
    return config.PLUGINS_PATH / pathlib.Path(plugin_name)


def does_plugin_exist(plugin_name: str) -> bool:
    """Checks if the plugin exists

    Args:
        plugin_name (str): The name of the plugin

    Returns:
        bool: Whether the plugin exists
    """
    plugins_path = get_plugin_path(plugin_name)
    if not plugins_path.exists():
        return False

    plugin_file_path = get_plugin_path(plugin_name)
    return plugin_file_path.is_file()


def get_plugin(plugin_name: str):
    if does_plugin_exist(plugin_name):
        plugin_path = get_plugin_path(plugin_name)
        spec = importlib.util.spec_from_file_location(plugin_name.split('.')[0], plugin_path)
        if spec:
            module = importlib.util.module_from_spec(spec)
            if module and spec.loader:
                spec.loader.exec_module(module)
                return module
            else:
                return POSSIBLE_PLUGINS[plugin_name]
        else:
            return POSSIBLE_PLUGINS[plugin_name]
    else:
        return POSSIBLE_PLUGINS[plugin_name]


def get_request_utils() -> RequestUtilsProtocol:
    """Gets the request utils plugin (if it exists) and ensures it conforms to the protocol

    Returns:
        RequestUtilsProtocol: The request utils protocol
    """
    plugin_name = "request_utils.py"
    original_module = POSSIBLE_PLUGINS[plugin_name]
    new_module = get_plugin(plugin_name)

    original_functions = inspect.getmembers(original_module, inspect.isfunction)

    for name, func in original_functions:
        if not hasattr(new_module, name):
            setattr(new_module, name, func)

    # Ensure new_module conforms to the protocol
    assert isinstance(new_module, RequestUtilsProtocol), f"Module {plugin_name} does not match expected interface"

    return new_module
