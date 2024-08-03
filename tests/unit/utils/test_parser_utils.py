from graphqler.utils.parser_utils import get_base_oftype, get_output_type


def test_get_base_oftype():
    # Test case 1
    oftype = {"kind": "NON_NULL", "name": None, "ofType": {"kind": "LIST", "name": None, "ofType": {"kind": "SCALAR", "name": "String", "ofType": None}}}
    expected_output = {"kind": "SCALAR", "name": "String", "ofType": None}
    assert get_base_oftype(oftype) == expected_output

    # Test case 2
    oftype = {"kind": "NON_NULL", "name": None, "ofType": {"kind": "SCALAR", "name": "Int", "ofType": None}}
    expected_output = {"kind": "SCALAR", "name": "Int", "ofType": None}
    assert get_base_oftype(oftype) == expected_output


def test_get_output_type():
    # Test case 1
    payload_name = "createUser"
    mutations = {
        "createUser": {"output": {"kind": "OBJECT", "name": "CreateUserPayload", "ofType": None, "type": "User"}},
        "updateUser": {"output": {"kind": "OBJECT", "name": "User", "ofType": None, "type": "User"}},
    }
    expected_output = "User"
    assert get_output_type(payload_name, mutations) == expected_output
