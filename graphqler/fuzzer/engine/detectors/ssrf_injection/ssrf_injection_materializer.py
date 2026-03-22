from typing import override

from graphqler.utils.api import API

from ...materializers.getter import Getter
from ...materializers.injection_materializer import InjectionMaterializer


# The main class that's being used
class SSRFInjectionMaterializer(InjectionMaterializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 20):
        super().__init__(api, fail_on_hard_dependency_not_met)
        self.api = api
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        self.max_depth = max_depth
        self.getter = SSRFInjectionGetter()


# Override the getters class to add custom getters for SQL injection
class SSRFInjectionGetter(Getter):
    def __init__(self):
        super().__init__()

    @override
    def get_random_string(self, input_name: str) -> str:
        if input_name == "url":
            return '"http://localhost:3000"'
        elif input_name == "uri":
            return '"http://localhost:3000"'
        elif input_name == "host":
            return '"localhost"'
        elif input_name == "path":
            return '"/"'
        elif input_name == "protocol":
            return '"http"'
        elif input_name == "port":
            return "3000"
        elif input_name == "ip":
            return ""
        elif input_name == "scheme":
            return '"http"'
        else:
            return super().get_random_string(input_name)
