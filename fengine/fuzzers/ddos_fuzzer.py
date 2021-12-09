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
    third:Todo(id: 3) {
        id
    }
    ...
}
"""


class DDOSFuzzer(Fuzzer):

    # Extended from parent class
    def create_fuzzed_queries(self, num_queries: int = 10000):
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
            request_param_string += f"{param['name']}: {self.get_fuzzable(param['type'])}, "

        request_param_string = request_param_string.rsplit(",", 1)[0]  # remove the last comma added
        return request_param_string + ")"

    # Adds body to request by recursively generating
    def generate_body_for_request(self, output_type: str) -> str:
        request_result_string = ""
        if output_type in self.datatypes:
            for key, value in self.datatypes[output_type]["params"].items():
                if value["type"] == "ID" or value["type"] == "String" or value["type"] == "Boolean":
                    request_result_string += key + ", "
                else:
                    nested_object = self.generate_body_for_request(self, value["type"])
                    request_result_string += f"{{{nested_object}}}"
        request_result_string = request_result_string.rsplit(",", 1)[0]  # remove the last comma added
        return request_result_string
