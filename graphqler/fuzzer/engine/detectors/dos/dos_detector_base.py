"""Base class and shared helpers for DoS detectors.

DoS detectors share a common vulnerability-signal heuristic: they look for server-side signals
that indicate the request was not gracefully rejected — server errors, timeouts, or explicit error
messages about resource limits being exceeded.
"""

import requests
from typing import Type

from graphqler.fuzzer.engine.detectors.detector import Detector
from graphqler.fuzzer.engine.materializers.materializer import Materializer

# HTTP status codes that indicate the server was overwhelmed rather than returning a controlled error
DOS_VULNERABLE_HTTP_CODES = {500, 503, 504}
DOS_POTENTIALLY_VULNERABLE_HTTP_CODES = {429, 502}

# Patterns in the response body that suggest the request was not safely rejected
DOS_ERROR_PATTERNS = [
    "timeout",
    "timed out",
    "maximum depth",
    "max depth",
    "query depth",
    "complexity",
    "query complexity",
    "too complex",
    "cost limit",
    "rate limit exceeded",
    "query too large",
    "depth limit",
    "field limit",
    "recursion",
    "fragment cycle",
    "circular",
    "loop detected",
    "exceeded",
    "stack overflow",
    "out of memory",
]

# Patterns whose *presence* indicates the server caught the issue — not vulnerable
DOS_SAFE_REJECTION_PATTERNS = [
    "cannot spread fragment",           # Apollo / graphql-js circular-fragment rejection
    "fragment would form a cycle",      # graphql-js >=16
    "fragment cycle detected",
    "contains a cycle",
]


class DOSDetector(Detector):
    """Shared base for DoS-style detectors.

    Subclasses only need to provide:
    - DETECTION_NAME (property)
    - materializer (property)

    The default _is_vulnerable / _is_potentially_vulnerable logic checks for the shared
    DoS signal patterns.  Subclasses may override for specialised logic.
    """

    @property
    def DETECTION_NAME(self) -> str:
        raise NotImplementedError

    @property
    def materializer(self) -> Type[Materializer]:
        raise NotImplementedError

    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        """Confirmed vulnerable: server returned a 5xx or a response body indicating an uncontrolled
        resource issue (not a clean validation rejection)."""
        if request_response.status_code in DOS_VULNERABLE_HTTP_CODES:
            return True
        text_lower = request_response.text.lower()
        # If the server safely rejected (e.g. "fragment would form a cycle"), it is NOT vulnerable
        if any(pat in text_lower for pat in DOS_SAFE_REJECTION_PATTERNS):
            return False
        return any(pat in text_lower for pat in DOS_ERROR_PATTERNS)

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        if request_response.status_code in DOS_POTENTIALLY_VULNERABLE_HTTP_CODES:
            return True
        return False

    def _get_evidence(self, graphql_response: dict, request_response: requests.Response | None) -> str:
        if request_response is None:
            return ""
        if request_response.status_code in DOS_VULNERABLE_HTTP_CODES | DOS_POTENTIALLY_VULNERABLE_HTTP_CODES:
            return f"HTTP {request_response.status_code}"
        text_lower = request_response.text.lower()
        for pat in DOS_ERROR_PATTERNS:
            if pat in text_lower:
                return f"matched DoS error pattern: '{pat}'"
        return ""
