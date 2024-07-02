from enum import Enum
from graphqler.constants import NO_DATA_COUNT_AS_SUCCESS


# Class to define the type of failure
class Result(Enum):
    EXTERNAL_FAILURE = {"type": "external_failure", "reason": "Failure happened outside of the fuzzer", "success": False}
    INTERNAL_FAILURE = {"type": "internal_failure", "reason": "Failure happened inside the fuzzer", "success": False}
    GENERAL_SUCCESS = {"type": "general_success", "reason": "General success", "success": True}
    HAS_DATA_SUCCESS = {"type": "has_data_success", "reason": "Success and has data", "success": True}
    NO_DATA_SUCCESS = {"type": "no_data_success", "reason": "Success and has no data", "success": NO_DATA_COUNT_AS_SUCCESS}

    def get_type(self) -> str:
        """Gets the type of the result

        Returns:
            str: Type
        """
        return self.value["type"]

    def get_reason(self) -> str:
        """Gets the reason of the result

        Returns:
            str: Reason
        """
        return self.value["reason"]

    def get_success(self) -> bool:
        """Gets whether or not the result is a success

        Returns:
            bool: True if success, False otherwise
        """
        return self.value["success"]
