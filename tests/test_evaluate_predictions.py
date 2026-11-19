import unittest
from scripts.evaluate_predictions import audit, wilson_lower


def entry(i, *, outcome="1", p="0.9", selected="1"):
    return {
        "fight_id": "test-" + str(i),
        "fight_utc": "2026-11-01T18:00:00+00:00",
        "feature_asof_utc": "2026-10-29T18:00:00+00:00",
        "prediction_utc": "2026-10-30T18:00:00+00:00",
        "p_a": p,
        "outcome_a": outcome,
        "selected": selected,
        "decimal_odds_selected": "1.15",
        "quote_utc": "2026-10-30T16:00:00+00:00",
    }


class EvaluatorTests(unittest.TestCase):
    def test_five_correct_not_99_9_proven(self):
        result = audit([entry(i) for i in range(5)], "2026-10-01T00:00:00+00:00")
        self.assertEqual(result["selected_accuracy"], 1.0)
        self.assertLess(result["wilson_95_lower"], .999)
        self.assertFalse(result["verified_99_9_claim"])

    def test_abstention_reported(self):
        result = audit([entry(1), entry(2, selected="0", outcome="0")],
                       "2026-10-01T00:00:00+00:00")
        self.assertEqual(result["selected_predictions"], 1)
        self.assertEqual(result["abstained"], 1)
        self.assertEqual(result["coverage"], .5)

    def test_no_future_features(self):
        row = entry(1)
        row["feature_asof_utc"] = "2026-11-02T00:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "timeline violation"):
            audit([row], "2026-10-01T00:00:00+00:00")

    def test_no_future_odds(self):
        row = entry(1)
        row["quote_utc"] = "2026-10-31T00:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "quote later"):
            audit([row], "2026-10-01T00:00:00+00:00")

    def test_duplicate_fights(self):
        with self.assertRaisesRegex(ValueError, "duplicate fight_id"):
            audit([entry(1), entry(1)], "2026-10-01T00:00:00+00:00")

    def test_timezone_required(self):
        row = entry(1)
        row["prediction_utc"] = "2026-10-30T18:00:00"
        with self.assertRaisesRegex(ValueError, "Timezone required"):
            audit([row], "2026-10-01T00:00:00+00:00")

    def test_incorrect_prediction_is_loss(self):
        result = audit([entry(1, outcome="0")], "2026-10-01T00:00:00+00:00")
        self.assertEqual(result["selected_accuracy"], 0.0)
        self.assertEqual(result["correct"], 0)

    def test_no_selected_predictions_not_100(self):
        result = audit([entry(1, selected="0")], "2026-10-01T00:00:00+00:00")
        self.assertIsNone(result["selected_accuracy"])

    def test_small_perfect_sample_not_99_9(self):
        self.assertLess(wilson_lower(100, 100), .999)
        self.assertGreater(wilson_lower(5000, 5000), .999)


if __name__ == "__main__":
    unittest.main()
