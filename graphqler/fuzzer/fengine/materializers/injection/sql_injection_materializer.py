from .injection_materializer import InjectionMaterializer
from graphqler.utils.api import API
from ..getter import Getter

from typing import override


# The main class that's being used
class SQLInjectionMaterializer(InjectionMaterializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 20):
        super().__init__(api, fail_on_hard_dependency_not_met)
        self.api = api
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        self.getter = SQLInjectionGetter()


# Override the getters class to add custom getters for SQL injection
class SQLInjectionGetter(Getter):
    def __init__(self):
        super().__init__()

    @override
    def get_random_string(self, input_name: str) -> str:
        return '"aaa \' OR 1=1--"'
