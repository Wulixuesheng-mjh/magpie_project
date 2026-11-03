import unittest

from intent_study.native import cut_middle, previous_fallback, read_intent, strict_number_format


class NativeBehaviorTests(unittest.TestCase):
    def test_first_ascii_number_is_native_behavior(self):
        for answer in ("2", "I choose 2 because...", "-2", "2.7"):
            self.assertEqual(read_intent(answer, ["a", "b"]), ("b", "2"))
        self.assertFalse(strict_number_format("I choose 2", 2))
        self.assertTrue(strict_number_format(" 2 ", 2))

    def test_zero_invalid_and_overflow(self):
        self.assertEqual(read_intent("0", ["a"]), (None, "0"))
        for answer in ("none", "3", "２", "9" * 100):
            with self.assertRaises(ValueError):
                read_intent(answer, ["a", "b"])

    def test_cut_uses_unicode_characters_not_bytes(self):
        text = "中" * 3000 + "文" * 1000 + "末"
        self.assertEqual(cut_middle(text), text[:3000] + "\n…\n" + text[-1000:])
        self.assertEqual(cut_middle("中" * 4000), "中" * 4000)

    def test_valid_none_must_not_inherit_previous(self):
        self.assertIsNone(previous_fallback(None, None, "a", ["a"])["intent"])
        self.assertEqual(previous_fallback(None, "timeout", "a", ["a"])["intent"], "a")
        self.assertIsNone(previous_fallback(None, "timeout", "removed", ["a"])["intent"])
