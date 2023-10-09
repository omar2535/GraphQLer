# Use small dictionary to replace parameters
# TODO: Hao

"""
Gives you the GraphqlRequest
Gives you the fuzzable paraemters


"""

from typing import List
from requests.api import request
from fengine.fuzzers.fuzzer import Fuzzer
from itertools import product
from graphqler_types.graphql_request import GraphqlRequest


class ReplaceParamsFuzzer(Fuzzer):

    # Extended from parent class
    def create_fuzzed_queries(self):
        queries = []
        query_params = self.generate_query_params()
        query_body = self.generate_query_body()
        for query_param in query_params:
            queries.append(self.generate_query(query_param=query_param, query_body=query_body))
        return queries

    def concat_params(self, product_turples: product):
        res_list = []
        for turple in product_turples:
            para_str = "("
            for param in turple:
                para_str += param
                para_str += ", "
            para_str = para_str[:-2] + ")"
            res_list.append(para_str)
        return res_list

    def generate_param_from_dict(self, param):
        fuzzable_list = self.get_fuzzable(param["type"], get_random_one=False)
        param_from_dict = []
        for p in fuzzable_list:
            param_from_dict.append(f"{param['name']}: {p}")
        return param_from_dict

    def generate_query_params(self):
        number_of_params = len(self.request.params)
        if number_of_params != 0:
            params_from_dict_list = []
            for param in self.request.params:
                param_from_dict = self.generate_param_from_dict(param)
                params_from_dict_list.append(param_from_dict)
            product_turples = product(*params_from_dict_list)
            query_params = self.concat_params(product_turples=product_turples)
        return query_params  # a list of param string

    def generate_query_body(self):
        return self.generate_body_for_request(self.request.res[0]["type"])

    def generate_query(self, query_param, query_body):
        query_type = self.request.type
        query_name = self.request.name
        string = f"""{query_type}{{
            {query_name}{query_param}{{
                {query_body}
            }}
        }}"""
        return string
