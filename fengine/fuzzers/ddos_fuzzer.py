# TODO: Omar

from fengine.fuzzers.fuzzer import Fuzzer

from fengine.fuzzers.constants import DEFAULT_DDOS_NUM
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
    third:Todo(id: 3) {
        id
    }
    ...
}
"""


class DDOSFuzzer(Fuzzer):

    # Extended from parent class
    def create_fuzzed_queries(self, num_queries: int = DEFAULT_DDOS_NUM):
        query_type = self.request.type
        query_name = self.request.name

        query_string = f"""{query_type} {{
            {self.create_many_requests(query_name, num_queries)}
        }}"""

        return [query_string]

    def create_many_requests(self, query_name: str, num_queries: int):
        requests = ""
        for i in range(0, num_queries):
            query_prepend = num2words(i).replace(" ", "")
            query = f"""
                {query_prepend}:{query_name}{self.generate_params_input()}{{
                    {self.generate_body_for_request(self.request.res[0]['type'])}
                }}
            """
            requests += query
        return requests

    # TODO: Add supported type for custom data-types
    def generate_params_input(self) -> str:
        request_param_string = "("
        for param in self.request.params:
            request_param_string += f"{param['name']}: {self.get_fuzzable(param['type'], get_random_one=True)}, "

        request_param_string = self.remove_last_comma(request_param_string)
        return request_param_string + ")"
