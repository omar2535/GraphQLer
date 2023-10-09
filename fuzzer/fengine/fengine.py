"""
Input: Method name string
Output: Array of query strings (refer to https://towardsdatascience.com/connecting-to-a-graphql-api-using-python-246dda927840)
"""

from fengine.fuzzers.fuzzer import Fuzzer
from typing import List, Dict


class Fengine(object):
    @staticmethod
    def fuzz(fuzzer: Fuzzer, request, datatypes: Dict = {}) -> List[str]:
        """
        Single method to call all fuzzers.

        Args:
            fuzzer (Fuzzer): Class of the fuzzer to use; IE. DDOSFuzzer, ReplaceParamsFuzzer, ect.
            request (GraphqlRequest): The GraphqlRequest object to be used

        Returns:
            List[str]: List of grpahql queries as string
        """
        fuzzer = fuzzer(request, datatypes=datatypes)
        return fuzzer.create_fuzzed_queries()
