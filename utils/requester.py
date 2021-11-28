"""
TODO: Hao
Return [[valid_seq], [bug_seq]]
"""
# class GraphQLRequest:

def send_request(request_sequence, endpoint):
    """
    Sends the requests to the specified endpoint
    Return the response (response code and body)
    """
    pass

# this is the pseudocode of render

#####

    

def readDictionary(file_path):
    # read dictionary text file into
    return 0
#####


DEFAULT_DICT = readDictionary("")


def getPrevSeq(seq):
    """
    get a list of requests except the last one

    :param seq: a sequence of requets where only the last one needs to be concretized
    :return:    a list of concrete requests
    """
    if len(seq) <= 1:
        return []
    else:
        return seq[:-1]


def getLastRequest(seq):
    """
    get the last request which need to be concretize

    :param seq: a sequence of requets where only the last one needs to be concretized
    :return:    the last request
    """
    if len(seq) < 1:
        raise Exception(f"Empty sequence!")
    else:
        return seq[len(seq) - 1]


def concretizeRequest(req, dict=DEFAULT_DICT, dynamic_dict=None):
    return


def concretizeDynamicRequest(req, dict=DEFAULT_DICT, dynamic_dict=None, dynamic_objects=None):
    return


def concatReq(seq, req):
    return


def executeSeq(prev_seq, last_req, dynamic_dict):
    if "require previous results" in last_req:
        require_dynamic_objects = True
        dynamic_objects = []
    seq = concatReq(prev_seq, last_req)

    for i, req in enumerate(seq):
        if i != len(seq) - 1:
            req_res = sendRequest(req)
            if require_dynamic_objects:
                dynamic_objects.append(parseRes(req_res))
        else:
            if require_dynamic_objects:
                # Problem:  what if previous requests produce many same time obejcts,
                # how to choose to fill the last request?
                # Possible solution: know what to expect(?)
                new_last_req = concretizeDynamicRequest(
                    req, dynamic_dict=dynamic_dict, dynamic_objects=dynamic_objects)
            req_res = sendRequest(req)
            status_code = getStatusCode(req_res)
            new_seq = concatReq(prev_seq, new_last_req)

            return status_code, new_seq


def renderSeq(seq):
    """
    main render function of a sequence

    :param seq: a sequence of requets where only the last one needs to be concretized
    :return:    a set of concrete sequences that have valid code (200) 
                and a set of concrete sequences that have 500 errors
    """

    valid_seq = []
    bug_seq = []

    prev_seq = getPrevSeq(seq)
    last_req = getLastRequest(seq)

    dynamic_dict = generateDynamicDict(prev_seq)

    last_req_list = concretizeRequest(last_req, dynamic_dict=dynamic_dict)

    for last_req in last_req_list:
        status_code, new_seq = executeSeq(prev_seq, last_req, dynamic_dict)
        if status_code in range(200, 300):
            valid_seq.append(new_seq)
        if status_code >= 500:
            bug_seq.append(new_seq)
    return [valid_seq, bug_seq]


if __name__ == "__main__":
    # res = renderSeq()
    # print(f"validSeq  : {res[0]}")
    # print(f"invalidSeq: {res[1]}")
    seq = ['1', '2']
    print(getLastRequest(seq))
    print(getPrevSeq(seq))



