from graphqler.fuzzer.fengine.utils import check_is_data_empty


test_dict_1 = {"key1": None, "key2": {"key3": None, "key4": {"key5": None, "key6": "Not None"}}}

test_dict_2 = {"key1": None, "key2": {"key3": None, "key4": {"key5": None, "key6": None}}}


def test_check_non_epty_data():
    assert check_is_data_empty(test_dict_1) is False


def test_check_empty_data():
    assert check_is_data_empty(test_dict_2) is True
