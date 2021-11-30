"""
Input: Method name string
Output: Array of query strings (refer to https://towardsdatascience.com/connecting-to-a-graphql-api-using-python-246dda927840)
"""

from fengine.fuzzers.fuzzer import Fuzzer
from utils.graphql_request import GraphqlRequest
from fuzzers.ddos_fuzzer import DDOSFuzzer
from fuzzers.replace_params_fuzzer import ReplaceParamsFuzzer


OPTIONS = {"ddos": DDOSFuzzer, "replace_params": ReplaceParamsFuzzer}


class Fengine(object):
    @staticmethod
    def fuzz(fuzz_option: str, request: GraphqlRequest):
        fuzzer: Fuzzer = OPTIONS[fuzz_option](request)
        return fuzzer.create_fuzzed_queries()
