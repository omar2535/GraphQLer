# TODO: Omar

from fengine.fuzzers.fuzzer import Fuzzer
from num2words import num2words

# DDOS-Fuzzer that is specifically used for query requests
"""
Example:

query evil {
    Todo(id: 1) {
        id,
        completed
    }
    second:Todo(id: 2) {
        id
    }
    ...
}
"""


class DDOSFuzzer(Fuzzer):

    # Extended from parent class
    def create_fuzzed_queries(self):
        query_type = self.request.type
        query_name = self.request.name

        string = f"""{query_type} {{
            {query_name} {{

            }}
        }}"""

        breakpoint()

        return [string]

    def create_many_requests(self, query_name: str, num_requests: int = 1000):
        # TODO:
        # Need to generate params input
        # Need to generate query output params
        requests = ""
        for i in range(0, num_requests):
            query_prepend = num2words(i).replace(" ", "")
            query = f"""
                {query_prepend}:{query_name}(){{

                }}
            """
            requests += query
        return requests

    # TODO: Add supported type for custom data-types
    def generate_params_input(self):
        request_param_string = "("
        for param in self.request.params:
            if param["type"] == "String":
                request_param_string += f"{param['name']}: {self.fuzzables['String'] or 'some_string'}"
            elif param["type"] == "Boolean":
                request_param_string += f"{param['name']}: {self.fuzzables['Boolean'] or 'False'}"
            elif param["type"] == "ID":
                request_param_string += f"{param['name']}: {self.fuzzables['ID'] or '1'}"
            else:
                raise "Not supported type"

    # TODO: Add body to the request
    def generate_body_for_request(self):

        pass
