from graphqler_types.graphql_request import GraphqlRequest

# Base class for all fuzzers
# All fuzzers extend this class


class Fuzzer:
    def __init__(self, graphql_request: GraphqlRequest):
        self.request = graphql_request

    # Override this method!
    def create_fuzzed_queries():
        raise "Change me"
