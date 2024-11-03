from ...materializers.injection_materializer import InjectionMaterializer
from graphqler.utils.api import API
from ...materializers.getter import Getter

from typing import override


# The main class that's being used
class OSCommandInjectionMaterializer(InjectionMaterializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 20):
        super().__init__(api, fail_on_hard_dependency_not_met)
        self.api = api
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        self.getter = OSCommandInjectionGetter()


# Override the getters class to add custom getters for SQL injection
class OSCommandInjectionGetter(Getter):
    def __init__(self):
        super().__init__()

    @override
    def get_random_string(self, input_name: str) -> str:
        random_str = ""
        if input_name.lower() == "host":
            random_str = "localhost"
        elif input_name.lower() == "port":
            random_str = "80"
        elif input_name.lower() == "path":
            random_str = "/ ; cat /etc/passwd"
        elif input_name.lower() == "scheme":
            random_str = "http"
        elif input_name.lower() == "cmd":
            random_str = "cat /etc/passwd"
        else:
            return super().get_random_string(input_name)

        return f"\"{random_str}\""
