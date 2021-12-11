"""Possible fuzzer list"""

from fengine.fuzzers.ddos_fuzzer import DDOSFuzzer
from fengine.fuzzers.replace_params_fuzzer import ReplaceParamsFuzzer


POSSIBLE_FUZZERS = {"ddos_fuzzer": DDOSFuzzer, "replace_params_fuzzer": ReplaceParamsFuzzer}
