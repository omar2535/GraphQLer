from typing import Dict
from fengine.fuzzers.defaults import DEFAULT_FUZZABLE
from graphqler_types.graphql_request import GraphqlRequest

# Base class for all fuzzers
# All fuzzers extend this class
# Access request param via self.request


class Fuzzer:
    def __init__(self, graphql_request: GraphqlRequest, fuzzables: Dict = {}, datatypes: Dict = {}):
        self.request = graphql_request
        self.fuzzables = fuzzables
        self.datatypes = datatypes

    # !!Override this method!!
    def create_fuzzed_queries():
        raise "Didn't override implemented fuzzer!"

    def get_fuzzable(self, fuzzable_type: str):
        """
        Gets parameters for fuzzables. First checks in the fuzzables dictionary, then checks
        in the defaults dictionary. If not found in either, then raises an exception.

        Args:
            type (str): type to look for in the fuzzable dictionary
        """
        if fuzzable_type in self.fuzzables:
            return self.fuzzables[fuzzable_type]
        elif fuzzable_type in DEFAULT_FUZZABLE:
            return DEFAULT_FUZZABLE[fuzzable_type]
        else:
            raise "Unsupported type"
