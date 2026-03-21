from typing import override

from graphqler.utils.api import API

from ...materializers.getter import Getter
from ...materializers.injection_materializer import InjectionMaterializer


# One payload per DB flavour; sleep duration is parameterised at construction time
# so the detector can pass config.TIME_BASED_SQL_SLEEP_SECONDS at runtime.
def _build_payloads(sleep_seconds: int) -> list[str]:
    s = sleep_seconds
    return [
        f"\"1' AND SLEEP({s})--\"",                       # MySQL / MariaDB
        f"\"1'; SELECT pg_sleep({s})--\"",                 # PostgreSQL
        f"\"1'; WAITFOR DELAY '0:0:{s}'--\"",              # MSSQL / SQL Server
        f"\"1' AND 1=BENCHMARK({s * 1_500_000},SHA1(1))--\"",  # MySQL alternative (CPU-based)
    ]


class TimeSQLInjectionMaterializer(InjectionMaterializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 20, sleep_seconds: int = 3):
        super().__init__(api, fail_on_hard_dependency_not_met)
        self.api = api
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        self.max_depth = max_depth
        self.getter = TimeSQLInjectionGetter(sleep_seconds=sleep_seconds)


class TimeSQLInjectionGetter(Getter):
    def __init__(self, sleep_seconds: int = 3):
        super().__init__()
        self._payloads = _build_payloads(sleep_seconds)
        self._index = 0

    @override
    def get_random_string(self, input_name: str) -> str:
        if input_name in ['filter', 'search', 'query', 'name', 'username', 'password', 'email', 'id', 'text', 'message', 'input', 'value']:
            # Rotate through payloads so each call gets a different DB-flavour
            payload = self._payloads[self._index % len(self._payloads)]
            self._index += 1
            return payload
        return super().get_random_string(input_name)
