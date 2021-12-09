# TODO: Omar

from fengine.fuzzers.fuzzer import Fuzzer


class DDOSFuzzer(Fuzzer):

    # Extended from parent class
    def create_fuzzed_queries(self):

        self.request.params
        return [""]
