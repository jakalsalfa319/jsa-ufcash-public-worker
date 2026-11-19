import math
import unittest

from scripts.precision_lab import (
    FEATURES, LOG_FIELDS, RATINGS, THRESHOLDS, lock_policy, summary, wilson_lower
)


class PrecisionLabTests(unittest.TestCase):
    def test_model_inputs_have_no_obvious_postfight_or_odds_fields(self):
        fields=set(FEATURES)|set(RATINGS)
        self.assertGreater(len(fields),35)
        for bad in ("winner","outcome","odds","red_odds","blue_odds","rank","imp","height","reach","age","fighter_id"):
            self.assertNotIn(bad,fields)
        self.assertFalse(any(x.startswith("mk_") for x in fields))

    def test_model_is_frozen_to_validation_gate(self):
        val=[.95]*40+[.65]*30+[.51]*30
        labels=[1]*36+[0]*4+[1]*19+[0]*11+[1]*16+[0]*14
        result=lock_policy(val,labels)
        self.assertIn(result["threshold"],THRESHOLDS)
        self.assertGreaterEqual(result["validation"]["selected"],25)
        self.assertGreaterEqual(result["validation"]["coverage"],.08)

    def test_confident_but_tiny_sample_does_not_pass_gate(self):
        p=[.99]*5+[.5]*95
        y=[1]*5+[0]*95
        locked=lock_policy(p,y)
        self.assertNotEqual(locked["threshold"],.95)
        self.assertFalse(locked.get("claim99_9Achieved",False))

    def test_no_prediction_when_empty(self):
        s=summary([],[])
        self.assertIsNone(s["accuracy"])
        self.assertIsNone(s["wilson95Lower"])

    def test_abstentions_accounted(self):
        s=summary([.9,.52,.1],[1,0,0],.8)
        self.assertEqual(s["selected"],2)
        self.assertAlmostEqual(s["coverage"],2/3)
        self.assertEqual(s["correct"],2)

    def test_invalid_probabilities_fail(self):
        with self.assertRaises(ValueError):
            summary([float("nan")],[1])
        with self.assertRaises(ValueError):
            summary([.9],[2])
        with self.assertRaises(ValueError):
            summary([.5,.7],[1])

    def test_small_perfect_accuracy_is_not_verified_target(self):
        self.assertLess(wilson_lower(10,10),.999)
        self.assertLess(wilson_lower(100,100),.999)
        self.assertGreater(wilson_lower(5000,5000),.999)

    def test_covered_full_and_filtered_are_distinct(self):
        p=[.9,.51,.8,.49]
        y=[1,1,1,0]
        full=summary(p,y)
        selective=summary(p,y,.75)
        self.assertEqual(full["selected"],4)
        self.assertEqual(selective["selected"],2)
        self.assertEqual(selective["coverage"],.5)


if __name__=="__main__":
    unittest.main()
