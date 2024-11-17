from enum import Enum
from graphqler import config
from typing import Optional


class ResultEnum(Enum):
    EXTERNAL_FAILURE = {"type": "external_failure", "reason": "Failure happened outside of the fuzzer", "success": False}
    INTERNAL_FAILURE = {"type": "internal_failure", "reason": "Failure happened inside the fuzzer", "success": False}
    GENERAL_SUCCESS = {"type": "general_success", "reason": "General success", "success": True}
    HAS_DATA_SUCCESS = {"type": "has_data_success", "reason": "Success and has data", "success": True}
    NO_DATA_SUCCESS = {"type": "no_data_success", "reason": "Success and has no data", "success": config.NO_DATA_COUNT_AS_SUCCESS}


class Result:
    def __init__(self,
                 result_enum: Optional[ResultEnum] = None,
                 payload: Optional[str] | Optional[list[str]] | dict = None,
                 errors: Optional[list] = None,
                 data: Optional[dict] = None,
                 status_code: Optional[int] = None,
                 graphql_response: Optional[dict] = None,
                 raw_response_text: Optional[str] = None):
        """Initializes the result object"""
        self._result_enum = result_enum
        self._payload = payload
        self._errors = errors
        self._data = data
        self._status_code = status_code
        self._graphql_response = graphql_response
        self._raw_response_text = raw_response_text

    def __eq__(self, other: object) -> bool:
        """
        Implement equality comparison for Result objects.
        Two Results are considered equal if they have the same content.
        """
        if not isinstance(other, Result):
            return NotImplemented

        return (
            self._result_enum == other._result_enum
            and self._payload == other._payload
            and self._errors == other._errors
            and self._data == other._data
            and self._status_code == other._status_code
            and self._graphql_response == other._graphql_response
            and self._raw_response_text == other._raw_response_text
        )

    def __hash__(self) -> int:
        """
        Implement hashing for Result objects.
        This allows Result objects to be used in sets and as dictionary keys.
        """
        return hash((
            self._result_enum,
            str(self._payload),
            str(self._errors),
            str(self._data),
            self._status_code,
            str(self._graphql_response),
            self._raw_response_text
        ))

    def __str__(self) -> str:
        """Returns a string representation of the result"""
        return f"Result<{self._result_enum} | {self._status_code} | {self.__hash__()}>"

    def __repr__(self) -> str:
        """Returns a string representation of the result"""
        return f"Result<{self._result_enum} | {self._status_code} | {self.__hash__()}>"

    # ----------------- Properties -----------------
    @property
    def result_enum(self) -> Optional[ResultEnum]:
        """Gets the result enum"""
        return self._result_enum

    @result_enum.setter
    def result_enum(self, result_enum):
        """Sets result enum"""
        self._result_enum = result_enum

    @property
    def payload(self) -> Optional[str] | Optional[list[str]] | dict:
        """Gets the payload string"""
        return self._payload

    @property
    def success(self) -> bool:
        """Dynamically retrieves success status"""
        if self._result_enum is None:
            return False
        if self._result_enum == ResultEnum.NO_DATA_SUCCESS:
            # Access config dynamically for NO_DATA_SUCCESS success status
            return config.NO_DATA_COUNT_AS_SUCCESS  # Replace with actual config
        return self._result_enum.value["success"]

    @property
    def type(self) -> str:
        """Gets the type of the result"""
        if self._result_enum is None:
            return "unknown"
        return self._result_enum.value["type"]

    @property
    def reason(self) -> str:
        """Gets the reason of the result"""
        if self._result_enum is None:
            return "unknown"
        return self._result_enum.value["reason"]

    @property
    def has_data(self) -> bool:
        """Checks if the result has data"""
        return self._data is not None

    @property
    def has_non_empty_data(self) -> bool:
        """Checks if the result has non-empty data"""
        return self.has_data and self._data != {}

    @property
    def has_errors(self) -> bool:
        """Checks if the result has errors"""
        return self._errors is not None and len(self._errors) > 0

    @property
    def has_status_code(self) -> bool:
        """Checks if the result has a status code"""
        return self._status_code is not None

    @property
    def data(self) -> dict:
        """Gets the data"""
        if self._data is None:
            return {}
        return self._data

    @data.setter
    def data(self, data):
        """Sets data"""
        self._data = data

    @property
    def status_code(self) -> int:
        """Gets the status code"""
        if self._status_code is None:
            return 0
        return self._status_code

    @status_code.setter
    def status_code(self, status_code):
        """Sets status code"""
        self._status_code = status_code

    @property
    def graphql_response(self) -> dict:
        """Gets the graphql response"""
        if self._graphql_response is None:
            return {}
        return self._graphql_response

    @graphql_response.setter
    def graphql_response(self, graphql_response):
        """Sets graphql response"""
        self._graphql_response = graphql_response
        if graphql_response is not None:
            if 'errors' in graphql_response:
                self._errors = graphql_response['errors']
            if 'data' in graphql_response:
                self._data = graphql_response['data']

    @property
    def raw_response_text(self) -> str:
        """Gets the raw response text"""
        if self._raw_response_text is None:
            return ''
        return self._raw_response_text

    @raw_response_text.setter
    def raw_response_text(self, raw_response_text):
        """Sets raw response text"""
        self._raw_response_text = raw_response_text

    @property
    def errors(self) -> list:
        """Gets the errors"""
        if self._errors is None:
            return []
        return self._errors

    @errors.setter
    def errors(self, errors):
        """Sets errors"""
        self._errors = errors

    @payload.setter
    def payload(self, payload):
        """Sets payload string"""
        self._payload = payload
