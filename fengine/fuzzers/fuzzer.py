from typing import Dict
from fengine.fuzzers.defaults import DEFAULT_FUZZABLE, DEFAULT_PRIMITIVES
from graphqler_types.graphql_request import GraphqlRequest
from random import randint

"""
Base class for all fuzzers
All fuzzers extend this class
Access request param via self.request
"""


class Fuzzer:
    def __init__(self, graphql_request: GraphqlRequest, fuzzables: Dict = {}, datatypes: Dict = {}):
        self.request = graphql_request
        self.fuzzables = fuzzables
        self.datatypes = datatypes

    # !!Override this method!!
    def create_fuzzed_queries():
        raise "Didn't override implemented fuzzer!"

    def get_fuzzable(self, fuzzable_type: str, get_random_one: bool = False):
        """
        Gets parameters for fuzzables. First checks in the fuzzables dictionary, then checks
        in the defaults dictionary. If not found in either, then raises an exception.

        Args:
            type (str): type to look for in the fuzzable dictionary
        """
        if fuzzable_type in self.fuzzables:
            if get_random_one:
                return self.fuzzables[fuzzable_type][randint(0, len(self.fuzzables[fuzzable_type]) - 1)]
            return self.fuzzables[fuzzable_type]
        elif fuzzable_type in DEFAULT_FUZZABLE:
            if get_random_one:
                return DEFAULT_FUZZABLE[fuzzable_type][randint(0, len(DEFAULT_FUZZABLE[fuzzable_type]) - 1)]
            return DEFAULT_FUZZABLE[fuzzable_type]
        else:
            raise "Unsupported type"

    # Checks if type is primitive
    def is_type_primitive(self, value_type: str) -> bool:
        """Checks if type is a primitive (case insensitive!)

        Args:
            value_type (str): type as a string

        Returns:
            bool: true if type is primitive, false otherwise
        """
        for primitive in DEFAULT_PRIMITIVES:
            if primitive.lower() == value_type.lower():
                return True
        return False

    # Adds body to request by recursively generating
    def generate_body_for_request(self, output_type: str) -> str:
        if output_type in self.datatypes:
            request_result_string = self.generate_body_for_datatypes_output_type(output_type)
        else:
            raise Exception("Output type not in datatypes!")
        request_result_string = self.remove_last_comma(request_result_string)
        return request_result_string

    # Generates a body for the specified datatype
    def generate_body_for_datatypes_output_type(self, output_type: str) -> str:
        request_result_string = ""
        for key, value in self.datatypes[output_type]["params"].items():
            if self.is_type_primitive(value["type"]):
                request_result_string += key + ", "
            else:
                nested_object = self.generate_body_for_datatypes_output_type(value["type"])
                request_result_string += f"{{{nested_object}}}"
        return request_result_string

    # Removes the last comma of the string and white space
    # IE. lol,5,ok,stuff,  -> lol,s,ok,stuff
    def remove_last_comma(self, input_string: str) -> str:
        return "".join(input_string.rsplit(",", 1)).strip()
