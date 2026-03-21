from typing import Type

import requests

from graphqler import config

from ..detector import Detector
from .nosql_injection_materializer import NoSQLInjectionMaterializer
from .blind_nosql_extractor import BlindNoSQLExtractor


# MongoDB-style operator injection payloads
NOSQL_INJECTION_STRINGS = [
    '"{$gt: \\"\\"}"',
    '"{$ne: null}"',
    '"{$regex: \\".*\\"}"',
    '"{$where: \\"1==1\\"}"',
    '"{$exists: true}"',
    '"{$nin: []}"',
    "\"' || '1'=='1\"",
    "\"; sleep(5000); var dummy=\"",
]

# Error messages commonly emitted by NoSQL databases (MongoDB, etc.)
NOSQL_ERROR_PATTERNS = [
    "casterror",
    "mongoerror",
    "mongo",
    "bson",
    "objectid",
    "e11000",                      # MongoDB duplicate key error
    "bad query",
    "not valid json",
    "$where",
    "failed to parse",
    "unknown operator",
    "invalid operator",
    "queryfailederror",
    "mongoparseerror",
    "cannot apply $",
    "invalid use of $",
]


class NoSQLInjectionDetector(Detector):
    @property
    def DETECTION_NAME(self) -> str:
        return "NoSQL Injection (NoSQLi)"

    @property
    def detect_only_once_for_api(self) -> bool:
        return False

    @property
    def detect_only_once_for_node(self) -> bool:
        return True

    @property
    def materializer(self) -> Type[NoSQLInjectionMaterializer]:
        return NoSQLInjectionMaterializer

    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        response_text_lower = request_response.text.lower()
        return any(pattern in response_text_lower for pattern in NOSQL_ERROR_PATTERNS)

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        if graphql_response is None or 'data' not in graphql_response or graphql_response['data'] is None:
            return False
        # Server returning data on a NoSQL operator payload suggests the input reached the DB query
        if request_response.status_code == 200 and graphql_response['data'] and any(kw in self.payload for kw in NOSQL_INJECTION_STRINGS):
            return True
        return False

    def _get_evidence(self, graphql_response: dict, request_response: requests.Response) -> str:
        response_text_lower = request_response.text.lower()
        for pattern in NOSQL_ERROR_PATTERNS:
            if pattern in response_text_lower:
                return f"matched NoSQL error pattern: '{pattern}'"
        if self._is_potentially_vulnerable(graphql_response, request_response):
            evidence = "server returned data on NoSQL operator payload (potential blind NoSQLi)"
            if config.NOSQLI_BLIND_EXTRACTION:
                extracted = BlindNoSQLExtractor(self.api.url, self.payload).extract()
                if extracted:
                    evidence += f"; blind extraction recovered value: '{extracted}'"
            return evidence
        return ""
