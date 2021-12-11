"""Fuzzer Defaults"""

DEFAULT_STRING = ['"some_string"', '""']
DEFAULT_BOOL = ["false", "true"]
DEFAULT_ID = ['"1"', '"0"']
DEFAULT_DDOS_NUM = 25

"""Primitives and fuzzables"""

DEFAULT_FUZZABLE = {"String": DEFAULT_STRING, "Boolean": DEFAULT_BOOL, "ID": DEFAULT_ID}
DEFAULT_PRIMITIVES = ["ID", "String", "Boolean"]
