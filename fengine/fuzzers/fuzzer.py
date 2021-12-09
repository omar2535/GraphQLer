from typing import Dict
from graphqler_types.graphql_request import GraphqlRequest

# Base class for all fuzzers
# All fuzzers extend this class
# Access request param via self.request


class Fuzzer:
    def __init__(self, graphql_request: GraphqlRequest, fuzzables: Dict = {}):
        self.request = graphql_request
        self.fuzzables = fuzzables

    # !!Override this method!!
    def create_fuzzed_queries():
        raise "Didn't override implemented fuzzer!"
