import unittest

from graphqler.fuzzer.engine.utils import check_is_data_empty

test_dict_1 = {"key1": None, "key2": {"key3": None, "key4": {"key5": None, "key6": "Not None"}}}

test_dict_2 = {"key1": None, "key2": {"key3": None, "key4": {"key5": None, "key6": None}}}


class TestFengineUtils(unittest.TestCase):
    def test_check_non_epty_data(self):
        self.assertFalse(check_is_data_empty(test_dict_1))

    def test_check_empty_data(self):
        self.assertTrue(check_is_data_empty(test_dict_2))

    def test_empty_list_is_empty(self):
        self.assertTrue(check_is_data_empty({"getCurrencies": []}))

    def test_populated_list_is_not_empty(self):
        self.assertFalse(check_is_data_empty({"getCurrencies": [{"id": "1"}]}))

    def test_list_of_empty_objects_is_empty(self):
        self.assertTrue(check_is_data_empty({"getCurrencies": [{}, {"id": None}]}))

    def test_list_with_one_populated_object_is_not_empty(self):
        self.assertFalse(check_is_data_empty({"getCurrencies": [{"id": None}, {"id": "1"}]}))

    def test_nested_empty_list_is_empty(self):
        self.assertTrue(check_is_data_empty({"getUser": {"notes": []}}))

    def test_nested_populated_list_is_not_empty(self):
        self.assertFalse(check_is_data_empty({"getUser": {"notes": [{"id": "1"}]}}))

    def test_list_of_lists(self):
        self.assertTrue(check_is_data_empty({"grid": [[], []]}))
        self.assertFalse(check_is_data_empty({"grid": [[], ["value"]]}))

    def test_falsy_scalars_are_data(self):
        # 0 and "" are values the API actually returned, not absence of data.
        self.assertFalse(check_is_data_empty({"count": 0}))
        self.assertFalse(check_is_data_empty({"name": ""}))

    def test_empty_payload_is_empty(self):
        self.assertTrue(check_is_data_empty({}))
