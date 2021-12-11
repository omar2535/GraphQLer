from typing_extensions import ParamSpecArgs
import requests
from typing import List
from typing import Dict
from fengine.fengine import Fengine
from fengine.fuzzers.replace_params_fuzzer import ReplaceParamsFuzzer
from fengine.fuzzers.ddos_fuzzer import DDOSFuzzer
from fengine.constants import POSSIBLE_FUZZERS
from graphqler_types.graphql_data_type import GraphqlDataType
from graphqler_types.graphql_request import GraphqlRequest
import copy

"""
TODO: Hao
Return [[valid_seq], [bug_seq]]

Call example:
from utils.requester import Requester
valid_seq, bug_seq = Requester(sequence, end_point_path).render()
"""

DEFAULT_URL = "http://localhost:3000"
HEADERS = {}
DEFAULT_DICT = None


class Requester:
    def __init__(self, sequence: List[GraphqlRequest], end_point_path: str, datatypes: Dict = {}):
        self.sequence = sequence
        self.end_point_path = end_point_path
        self.prev_seq = self.get_prev_seq(sequence)
        self.last_req_original = self.get_last_request(sequence)
        self.datatypes = datatypes

    @staticmethod
    def get_prev_seq(seq):
        """
        get a list of requests except the last one

        :param seq: a sequence of requets where only the last one needs to be concretized
        :return:    a list of concrete requests
        """
        if len(seq) <= 1:
            return []
        else:
            return seq[:-1]

    @staticmethod
    def get_last_request(seq):
        """
        get the last request which need to be concretize

        :param seq: a sequence of requets where only the last one needs to be concretized
        :return:    the last request
        """
        if len(seq) < 1:
            raise Exception(f"Empty sequence!")
        else:
            return seq[len(seq) - 1]

    @staticmethod
    def concat_req(seq, req):
        """
        Concat one sequence of requests and last request

        :param seq: list
        :param req: GraphQLRequest
        :return:    a list of requests
        """
        new_seq = []
        for r in seq:
            new_seq.append(r)
        new_seq.append(req)
        return new_seq

    def send_request(self, request: GraphqlRequest):
        """
        Sends the requests to the specified endpoint
        Return the response (response code and body)
        """
        return requests.post(self.end_point_path, json={"query": request.body}, headers=HEADERS)

    # TODO:
    def generate_dynamic_dict(self):
        """
        TODO: generate a dict of expected dyanamic objects

        :param seq: a sequence of requets where every request is concretized
        :return:    a dict of dynamic objects
        """
        dynamic_dict = {}
        return dynamic_dict

    def concretize_request(self, req, dict=DEFAULT_DICT, dynamic_dict=None):
        return

    def concretize_dynamic_request(self, req, dict=DEFAULT_DICT, dynamic_dict=None, dynamic_objects=None):
        return

    # def parse_res(self, response):
    #     # TODO
    #     return

    def execute_seq(self, last_req: GraphqlRequest, dynamic_dict=None):
        # if "require previous results" in last_req:
        #     require_dynamic_objects = True
        #     dynamic_objects = []

        seq = self.concat_req(self.prev_seq, last_req)

        for i, req in enumerate(seq):
            if i != len(seq) - 1:
                req_res = self.send_request(req)
                # check response code
                if req_res.status_code != 200:
                    # raise f"Previous request #{i} error"
                    pass
                # if require_dynamic_objects:
                #     dynamic_objects.append(parse_res(req_res))
            else:
                # if require_dynamic_objects:
                #     last_req = concretize_dynamic_request(
                #         req, dynamic_dict=dynamic_dict, dynamic_objects=dynamic_objects) # call fuzz engine
                req_res = self.send_request(req)
                status_code = req_res.status_code
                new_seq = self.concat_req(self.prev_seq, last_req)
                return status_code, new_seq

    def req_str_to_obj(self, last_req_str_list):
        last_req_list = []
        for last_req_str in last_req_str_list:
            last_req = copy.deepcopy(self.last_req_original)
            last_req.set_body(body=last_req_str)
            last_req_list.append(last_req)
        return last_req_list

    def render(self):
        """
        main render function of a sequence

        :param seq: a sequence of requets where only the last one needs to be concretized
        :return:    a set of concrete sequences that have valid code (200)
                    and a set of concrete sequences that have 500 errors
        """

        valid_seq = []
        bug_seq = []

        # dynamic_dict = self.generate_dynamic_dict()

        # last_req_list = self.concretize_request(dynamic_dict=dynamic_dict)  # call fuzz engine
        # TODO: call request

        # last_req_list = Fengine().fuzz(ReplaceParamsFuzzer(self.last_req_original, datatypes=self.datatypes), self.last_req_original)
        last_req_str_list = Fengine.fuzz(ReplaceParamsFuzzer, self.last_req_original, self.datatypes)
        last_req_list = self.req_str_to_obj(last_req_str_list)

        for last_req in last_req_list:
            status_code, new_seq = self.execute_seq(last_req)
            if status_code in range(200, 300):
                valid_seq.append(new_seq)
            if status_code >= 500:
                bug_seq.append(new_seq)
        return [valid_seq, bug_seq]

    def simple_fuzz_render(self, fuzzers):
        valid_seq = []
        bug_seq = []
        requests_str_list = []
        for fuzzer in fuzzers:
            requests_str_list.extend(Fengine.fuzz(POSSIBLE_FUZZERS[fuzzer], self.last_req_original, self.datatypes))
        # if "ddos_fuzzer" in fuzzers:
        #     requests_str_list.extend(Fengine.fuzz(DDOSFuzzer, self.last_req_original, self.datatypes))
        # if "param_replace_fuzzer" in fuzzers:
        #     requests_str_list.extend(Fengine.fuzz(ReplaceParamsFuzzer, self.last_req_original, self.datatypes))

        last_req_list = self.req_str_to_obj(requests_str_list)

        for last_req in last_req_list:
            status_code, new_seq = self.execute_seq(last_req)
            if status_code in range(200, 300):
                valid_seq.append(new_seq)
            else:
                bug_seq.append({"seq": new_seq, "status_code": status_code})
        return [valid_seq, bug_seq]
