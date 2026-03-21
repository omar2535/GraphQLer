from typing import override

from graphqler.utils.api import API

from ...materializers.getter import Getter
from ...materializers.injection_materializer import InjectionMaterializer


class NoSQLInjectionMaterializer(InjectionMaterializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 20):
        super().__init__(api, fail_on_hard_dependency_not_met)
        self.api = api
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        self.max_depth = max_depth
        self.getter = NoSQLInjectionGetter()


class NoSQLInjectionGetter(Getter):
    def __init__(self):
        super().__init__()

    @override
    def get_random_string(self, input_name: str) -> str:
        # Target fields most likely to be passed directly to a NoSQL query
        if input_name in ['filter', 'search', 'query', 'name', 'username', 'password', 'email', 'id', 'text', 'input', 'value', 'where']:
            return '"{$gt: \\"\\"}"'
        else:
            return super().get_random_string(input_name)
