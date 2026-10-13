"""Compare one private operation across authentication profiles."""

from __future__ import annotations

from typing import Any

from graphqler.fuzzer.engine.types import Result
from graphqler.fuzzer.engine.types.profile import RuntimeProfile
from graphqler.utils import detection_writer
from graphqler.utils.stats import Stats


class AuthorizationDifferentialDetector:
    """Report private data returned to anonymous or alternate identities.

    Classification is deliberately performed by the caller. This detector only
    compares responses for an operation already classified as user-scoped.
    """

    DETECTION_NAME = "AUTHORIZATION_DIFFERENTIAL"

    @staticmethod
    def _operation_data(response: Any, operation_name: str) -> Any:
        if isinstance(response, list):
            values = []
            for event in response:
                value = AuthorizationDifferentialDetector._operation_data(event, operation_name)
                if value is not None:
                    values.append(value)
            return values or None
        if not isinstance(response, dict):
            return None
        data = response.get("data")
        if isinstance(data, dict):
            return data.get(operation_name)
        return None

    @staticmethod
    def _field_paths(value: Any, prefix: str = "") -> list[str]:
        if isinstance(value, dict):
            paths: list[str] = []
            for key, nested in value.items():
                child = f"{prefix}.{key}" if prefix else key
                paths.extend(AuthorizationDifferentialDetector._field_paths(nested, child))
            return paths
        if isinstance(value, list):
            paths: list[str] = []
            for nested in value:
                paths.extend(AuthorizationDifferentialDetector._field_paths(nested, prefix))
            return paths
        return [prefix] if prefix and value is not None else []

    def detect(
        self,
        operation_name: str,
        primary_result: Result,
        profile_results: list[tuple[RuntimeProfile, Result]],
        stats: Stats,
    ) -> None:
        """Compare successful alternate-profile responses with the primary response."""
        primary_data = self._operation_data(primary_result.graphql_response, operation_name)
        if primary_data is None:
            return

        for profile, result in profile_results:
            alternate_data = self._operation_data(result.graphql_response, operation_name)
            if not result.success or alternate_data is None:
                continue
            exact_match = alternate_data == primary_data
            anonymous = not profile.auth_token and not profile.headers
            access_kind = "anonymous" if anonymous else f"profile '{profile.name}'"
            exposed_fields = sorted(set(self._field_paths(alternate_data)))
            fields_evidence = ", ".join(exposed_fields[:12]) or "<scalar>"
            confirmed = exact_match and anonymous
            if exact_match:
                evidence = f"Private operation returned the same non-null data to {access_kind} as to the primary profile; exposed fields: {fields_evidence}"
            else:
                evidence = f"Private operation returned non-null data to {access_kind}; data differed from the primary response; exposed fields: {fields_evidence}"
            payload = result.payload if isinstance(result.payload, str) else ""
            stats.add_vulnerability(
                self.DETECTION_NAME,
                operation_name,
                is_vulnerable=confirmed,
                potentially_vulnerable=True,
                payload=payload,
                evidence=evidence,
            )
            detection_writer.write_from_detector(
                vuln_name=self.DETECTION_NAME,
                node_name=operation_name,
                is_vulnerable=confirmed,
                potentially_vulnerable=True,
                payload=payload,
                graphql_response=result.graphql_response,
                status_code=result.status_code,
                evidence=evidence,
            )
