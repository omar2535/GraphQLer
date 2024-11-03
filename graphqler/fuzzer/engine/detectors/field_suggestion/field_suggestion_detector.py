from typing import Type

import requests

from .field_suggestion_materializer import FieldSuggestionMaterializer
from ..detector import Detector


class FieldSuggestionsDetector(Detector):
    """Field Suggestions Detector
    """
    @property
    def DETECTION_NAME(self) -> str:
        return "Field Suggestions Enabled"

    @property
    def detect_only_once_for_api(self) -> bool:
        return True

    @property
    def detect_only_once_for_node(self) -> bool:
        return True

    @property
    def materializer(self) -> Type[FieldSuggestionMaterializer]:
        return FieldSuggestionMaterializer

    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        return ("did you mean" in str(graphql_response['errors'][0]['message']).lower()
                or "did you mean" in request_response.text.lower())

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        return self._is_vulnerable(graphql_response, request_response)
