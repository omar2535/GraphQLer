from enum import Enum
from graphqler import config  # Import the config dynamically


class Result(Enum):
    EXTERNAL_FAILURE = {
        "type": "external_failure",
        "reason": "Failure happened outside of the fuzzer",
        "success": False,
        "errors": None,
        "data": None,
        "status_code": None,
        "raw_response_text": None,
    }
    INTERNAL_FAILURE = {
        "type": "internal_failure",
        "reason": "Failure happened inside the fuzzer",
        "success": False,
        "errors": None,
        "data": None,
        "status_code": None,
        "raw_response_text": None,
    }
    GENERAL_SUCCESS = {
        "type": "general_success",
        "reason": "General success",
        "success": True,
        "errors": None,
        "data": None,
        "status_code": None,
        "raw_response_text": None
    }
    HAS_DATA_SUCCESS = {
        "type": "has_data_success",
        "reason": "Success and has data",
        "success": True,
        "errors": None,
        "data": None,
        "status_code": None,
        "raw_response_text": None
    }
    NO_DATA_SUCCESS = {
        "type": "no_data_success",
        "reason": "Success and has no data",
        "success": config.NO_DATA_COUNT_AS_SUCCESS,
        "errors": None,
        "data": None,
        "status_code": None,
        "raw_response_text": None,
    }

    @property
    def success(self) -> bool:
        """Dynamically retrieves success status, taking config into account for NO_DATA_SUCCESS"""
        if self == Result.NO_DATA_SUCCESS:
            # Access config dynamically for NO_DATA_SUCCESS success status
            return config.NO_DATA_COUNT_AS_SUCCESS
        return self.value["success"]

    @property
    def type(self) -> str:
        """Gets the type of the result"""
        return self.value["type"]

    @property
    def reason(self) -> str:
        """Gets the reason of the result"""
        return self.value["reason"]
