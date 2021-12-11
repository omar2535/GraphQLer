"""
Graphler - main start
"""

import sys
from fengine.fuzzers import ddos_fuzzer
from utils.grammar_parser import GrammarParser
from utils.orchestrator import Orchestrator
from utils.requester import Requester
from fengine.fuzzers.constants import ALL_FUZEERS
from fengine.fuzzers.ddos_fuzzer import DDOSFuzzer
from fengine.fuzzers.replace_params_fuzzer import ReplaceParamsFuzzer
import re


def parse_fuzzer_arg(fuzzers: str):
    valid_fuzzers = []
    fuzzers = fuzzers.strip().replace(" ", "").split(",")
    for f in fuzzers:
        if f not in ALL_FUZEERS:
            # TODO: error handle
            print(f"(-) Error: Fuzzer {f} doesn't exist!")
        else:
            if f not in valid_fuzzers:
                valid_fuzzers.append(f)
    return valid_fuzzers


def main(grammar_file_path, end_point_path, fuzzers):
    grammar_parser = GrammarParser(grammar_file_path)
    graph = grammar_parser.generate_dependency_graph()
    datatypes = grammar_parser.get_datatypes()

    valid = []
    invalid = []
    for node in graph.nodes:
        requester = Requester([node], end_point_path, datatypes).simple_fuzz_render(fuzzers)
        valid.extend(requester[0])
        invalid.extend(requester[1])
    print(f"(+) -----------------------------------------------")
    print(f"(+) {len(valid)} valid request:")
    for seq in valid:
        for req in seq:
            query_string = re.sub("\\s+", " ", req.body)
            print(f"(+) {query_string}")
    print(f"(+) -----------------------------------------------")
    print(f"(+) {len(invalid)} invalid request:")
    for seq in invalid:
        query_string = ""
        print(f"-------------------------------- Status Code: {seq['status_code']}")
        for req in seq["seq"]:
            query_string = "".join(re.sub("\\s+", " ", req.body))
            print(f"(+) {query_string}")


if __name__ == "__main__":
    number_of_arguments = 3

    if len(sys.argv) < number_of_arguments + 1:
        print(f"(+) Requires {number_of_arguments} arguments")
        print(
            f'(+) Example usage: python3 simple-fuzzer.py examples/grammar-example.yml http://localhost:3000 "ddos_fuzzer,param_replace_fuzzer"'
        )
        sys.exit()

    file_name = sys.argv[0]
    grammar_file_path = sys.argv[1]
    end_point_path = sys.argv[2]
    fuzzers = parse_fuzzer_arg(sys.argv[3])
    prompt_string = "(+) Valid fuzzers: "
    for fuzzer in fuzzers:
        prompt_string += " " + str(fuzzer) + ","

    print(prompt_string)

    print("(+) Starting Graphler program")
    main(grammar_file_path, end_point_path, fuzzers)
    print("(+) Ending Graphler program")
