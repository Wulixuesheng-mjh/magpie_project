import unittest

from intent_study.core import grouped_split, metrics, validate


def sample(sid, text, label="a", **extra):
    return dict(id=sid, text=text, label=label, conversation_id=sid, source_group=sid,
                source_ref="debug-only", language="zh", provenance="synthetic_debug", **extra)


class CoreTests(unittest.TestCase):
    def test_transitive_groups_never_leak(self):
        rows = [sample(str(i), f"text {i}", "a" if i % 2 else "b") for i in range(30)]
        rows[0]["conversation_id"] = rows[1]["conversation_id"]
        rows[1]["source_group"] = rows[2]["source_group"]
        result = grouped_split(rows)
        self.assertEqual(result, grouped_split(rows))
        self.assertEqual(len({r["split"] for r in result[:3]}), 1)
        self.assertEqual(validate(result, ["a", "b"]), [])

    def test_formal_rejects_generated_and_unreviewed(self):
        errors = validate([sample("1", "example")], ["a"], formal=True)
        self.assertTrue(any("synthetic" in e for e in errors))
        self.assertTrue(any("adjudicated" in e for e in errors))

    def test_normalized_duplicates_and_cross_split(self):
        a, b = sample("1", "Ａ B"), sample("2", "a   b")
        a.update(split="train", conversation_id="shared")
        b.update(split="test", conversation_id="shared")
        errors = validate([a, b], ["a"])
        self.assertTrue(any("duplicate" in e for e in errors))
        self.assertTrue(any("crosses splits" in e for e in errors))

    def test_failure_and_abstention_remain_in_denominator(self):
        rows = [sample("1", "one"), sample("2", "two", "b"), sample("3", "three", "b")]
        predictions = [dict(id="1", label="a", elapsed_ms=10),
                       dict(id="2", label=None, error="timeout", elapsed_ms=8000)]
        result = metrics(rows, predictions, ["a", "b"])
        self.assertAlmostEqual(result["accuracy"], 1 / 3)
        self.assertAlmostEqual(result["coverage"], 1 / 3)
        self.assertEqual(result["macro_f1"], .5)
        self.assertEqual(result["errors"]["missing_prediction"], 1)

    def test_other_is_a_label_not_abstention(self):
        result = metrics([sample("1", "hello", "other")], [dict(id="1", label="other")], ["other"])
        self.assertEqual(result["coverage"], 1)
        self.assertEqual(result["accuracy"], 1)

    def test_same_followup_with_different_context_is_valid(self):
        a, b = sample("1", "继续"), sample("2", "继续")
        a["context"] = [{"role": "user", "content": "编写测试"}]
        b["context"] = [{"role": "user", "content": "解释函数"}]
        self.assertEqual(validate([a, b], ["a"]), [])

    def test_duplicate_and_foreign_predictions_fail(self):
        rows = [sample("1", "one")]
        with self.assertRaises(ValueError):
            metrics(rows, [dict(id="2", label="a")], ["a"])
        with self.assertRaises(ValueError):
            metrics(rows, [dict(id="1", label="a")] * 2, ["a"])


if __name__ == "__main__":
    unittest.main()
