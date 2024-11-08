from graphqler.config import PLUGINS_PATH
from graphqler.utils import request_utils

import importlib.util
import pathlib
import sys
import string
import secrets


# The possible plugins and their map to the original module in GraphQLer
POSSIBLE_PLUGINS = {
    "request_utils.py" : request_utils
}


class PluginsHandler:
    def __init__(self, path: pathlib.Path = pathlib.Path(PLUGINS_PATH)):
        self.plugins_path = pathlib.Path(path)

    def set_plugins(self):
        for plugin_name, module in POSSIBLE_PLUGINS.items():
            if self.does_plugin_exist(plugin_name):
                plugin_path = self.get_plugin_path(plugin_name)
                new_module = self.__load_module(plugin_path, plugin_name)
                for attr in dir(new_module):
                    if callable(getattr(new_module, attr)):
                        setattr(module, attr, getattr(new_module, attr))

    def does_plugin_exist(self, plugin_name) -> bool:
        if not self.plugins_path.exists():
            return False

        plugin_file_path = self.get_plugin_path(plugin_name)

        if not plugin_file_path.is_file():
            return False

        return True

    def get_dynamic_headers_module(self):
        if not self.does_plugin_exist("dynamic_headers.py"):
            return request_utils
        else:
            plugin_path = self.get_plugin_path("dynamic_headers.py")
            return self.__load_module(plugin_path, "dynamic_headers")

    def get_plugin_path(self, plugin_name) -> pathlib.Path:
        return self.plugins_path / plugin_name

    def __gensym(self, length=32, prefix="gensym_"):
        """
        generates a fairly unique symbol, used to make a module name,
        used as a helper function for load_module

        :return: generated symbol
        """
        alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits
        symbol = "".join([secrets.choice(alphabet) for i in range(length)])

        return prefix + symbol

    def __load_module(self, source, module_name=None):
        """
        reads file source and loads it as a module

        :param source: file to load
        :param module_name: name of module to register in sys.modules
        :return: loaded module
        """

        if module_name is None:
            module_name = self.__gensym()

        spec = importlib.util.spec_from_file_location(module_name, source)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module {module_name} from {source}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        return module
