from enum import Enum


# Class to define the type of failure
class Result(Enum):
    EXTERNAL_FAILURE = {"type": "external_failure", "reason": "Failure happened outside of the fuzzer", "success": False}
    INTERNAL_FAILURE = {"type": "internal_failure", "reason": "Failure happened inside the fuzzer", "success": False}
    GENERAL_SUCCESS = {"type": "general_success", "reason": "General success", "success": True}
