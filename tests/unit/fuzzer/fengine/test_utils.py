import unittest

from graphqler.fuzzer.fengine.utils import check_is_data_empty

test_dict_1 = {"key1": None, "key2": {"key3": None, "key4": {"key5": None, "key6": "Not None"}}}

test_dict_2 = {"key1": None, "key2": {"key3": None, "key4": {"key5": None, "key6": None}}}


class TestFengineUtils(unittest.TestCase):
    def test_check_non_epty_data(self):
        self.assertFalse(check_is_data_empty(test_dict_1))

    def test_check_empty_data(self):
        self.assertTrue(check_is_data_empty(test_dict_2))
