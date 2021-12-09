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

        request_param_string = self.remove_last_comma(request_param_string)
        return request_param_string + ")"

    # Adds body to request by recursively generating
    def generate_body_for_request(self, output_type: str) -> str:
        if output_type in self.datatypes:
            request_result_string = self.generate_body_for_datatypes_output_type(output_type)
        else:
            raise Exception("Output type not in datatypes!")
        request_result_string = self.remove_last_comma(request_result_string)
        return request_result_string

    # Generates a body for the specified datatype
    def generate_body_for_datatypes_output_type(self, output_type: str) -> str:
        request_result_string = ""
        for key, value in self.datatypes[output_type]["params"].items():
            if self.is_type_primitive(value["type"]):
                request_result_string += key + ", "
            else:
                nested_object = self.generate_body_for_datatypes_output_type(value["type"])
                request_result_string += f"{{{nested_object}}}"
        return request_result_string

    # Removes the last comma of the string and white space
    # IE. lol,5,ok,stuff  -> lol,s,ok,stuff
    def remove_last_comma(self, input_string: str) -> str:
        return "".join(input_string.rsplit(",", 1)).strip()
