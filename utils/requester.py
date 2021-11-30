"""
TODO: Hao
Return [[valid_seq], [bug_seq]]
"""
# class GraphQLRequest:


from typing_extensions import ParamSpecArgs


def send_request(request_sequence, endpoint):
    """
    Sends the requests to the specified endpoint
    Return the response (response code and body)
    """
    pass


DEFAULT_DICT = None


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


def generate_dynamic_dict(seq):
    """
    TODO: generate a dict of expected dyanamic objects

    :param seq: a sequence of requets where every request is concretized
    :return:    a dict of dynamic objects
    """
    dynamic_dict = {}
    return dynamic_dict


def concretize_request(req, dict=DEFAULT_DICT, dynamic_dict=None):
    return


def concretize_dynamic_request(req, dict=DEFAULT_DICT, dynamic_dict=None, dynamic_objects=None):
    return


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


def parse_res(response):
    # TODO
    return


def get_status_code(req_res):
    pass


def execute_seq(prev_seq, last_req, dynamic_dict):
    if "require previous results" in last_req:
        require_dynamic_objects = True
        dynamic_objects = []

    seq = concat_req(prev_seq, last_req)

    for i, req in enumerate(seq):
        if i != len(seq) - 1:
            req_res = send_request(req)
            # check response code
            if require_dynamic_objects:
                dynamic_objects.append(parse_res(req_res))
        else:
            if require_dynamic_objects:
                new_last_req = concretize_dynamic_request(
                    req, dynamic_dict=dynamic_dict, dynamic_objects=dynamic_objects
                )  # call fuzz engine
            req_res = send_request(req)
            status_code = get_status_code(req_res)
            new_seq = concat_req(prev_seq, new_last_req)

            return status_code, new_seq


def render_seq(seq):
    """
    main render function of a sequence

    :param seq: a sequence of requets where only the last one needs to be concretized
    :return:    a set of concrete sequences that have valid code (200)
                and a set of concrete sequences that have 500 errors
    """

    valid_seq = []
    bug_seq = []

    prev_seq = get_prev_seq(seq)
    last_req = get_last_request(seq)

    dynamic_dict = generate_dynamic_dict(prev_seq)

    last_req_list = concretize_request(last_req, dynamic_dict=dynamic_dict)  # call fuzz engine

    for last_req in last_req_list:
        status_code, new_seq = execute_seq(prev_seq, last_req, dynamic_dict)
        if status_code in range(200, 300):
            valid_seq.append(new_seq)
        if status_code >= 500:
            bug_seq.append(new_seq)
    return [valid_seq, bug_seq]


if __name__ == "__main__":
    seq = ["1", "2"]
    print(get_last_request(seq))
    print(get_prev_seq(seq))
