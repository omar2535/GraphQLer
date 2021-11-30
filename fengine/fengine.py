"""
Input: Method name string
Output: Array of query strings (refer to https://towardsdatascience.com/connecting-to-a-graphql-api-using-python-246dda927840)
"""

from fengine.fuzzers.fuzzer import Fuzzer
from types.graphql_request import GraphqlRequest
from typing import List


class Fengine(object):
    def fuzz(fuzzer: Fuzzer, request: GraphqlRequest) -> List[str]:
        """
        Single method to call all fuzzers.

        Args:
            fuzzer (Fuzzer): Class of the fuzzer to use; IE. DDOSFuzzer, ReplaceParamsFuzzer, ect.
            request (GraphqlRequest): The GraphqlRequest object to be used

        Returns:
            List[str]: List of grpahql queries as string
        """
        fuzzer = fuzzer(request)
        return fuzzer.create_fuzzed_queries()
