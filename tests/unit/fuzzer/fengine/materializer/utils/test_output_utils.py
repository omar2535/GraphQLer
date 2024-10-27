import unittest

from graphqler.fuzzer.fengine.materializers.utils.materialization_utils import is_valid_object_materialization, remove_consecutive_characters


class TestOutputUtils(unittest.TestCase):
    def test_is_valid_object_materialization(self):
        self.assertTrue(is_valid_object_materialization("abc {}") is False)
        self.assertTrue(is_valid_object_materialization("abc(filter:1) {}") is False)
        self.assertTrue(is_valid_object_materialization("abc(filter: {def: 123}) {def }") is True)
        self.assertTrue(is_valid_object_materialization("abc {def}") is True)
        self.assertTrue(is_valid_object_materialization("abc {, , ,}") is False)
        self.assertTrue(is_valid_object_materialization("abc {def, def, def}") is True)
        self.assertTrue(
            is_valid_object_materialization(
                'cards(filter: {status_type: "C223828YUY",},) {expiration_date,id,masked_card_number,, ,needs_activation,projected_arrival_date,status_type,temporary,uuid,, ,virtual,},, ,'
            )
            is True
        )
        self.assertTrue(is_valid_object_materialization("rewards {credit_builder {rewards_hub_screen}}"))
        self.assertTrue(is_valid_object_materialization("enrollment_screen{body,footer_text_markdown,image_url,title,}"))

    def test_remove_consecutive(self):
        assert remove_consecutive_characters("aaabbbccc", "a") == "abbbccc"
        assert remove_consecutive_characters("hellooo!!!", "o") == "hello!!!"
