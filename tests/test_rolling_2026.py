import unittest
import datetime as dt
from scripts.rolling_2026 import (
    QUARTERS, FAMILIES, SELECTION_THRESHOLD, validate_temporal, canonical_date
)


class Rolling2026Guards(unittest.TestCase):
    def test_fixed_four_families_and_threshold(self):
        self.assertEqual(FAMILIES,("logistic_weak","hist_boost","xgboost","catboost"))
        self.assertEqual(SELECTION_THRESHOLD,.75)

    def test_all_quarters_are_strictly_chronological(self):
        for quarter,calibration_start,end in QUARTERS:
            a=canonical_date(calibration_start)
            b=canonical_date(quarter)
            c=canonical_date(end)
            self.assertLess(a,b)
            self.assertLess(b,c)
            self.assertLessEqual((b-a).days,92)

    def test_prior_only_boundaries_pass(self):
        validate_temporal(
            [dt.date(2025,12,31)-dt.timedelta(days=90)],
            [dt.date(2026,1,2),dt.date(2026,3,31)],
            [dt.date(2026,4,1),dt.date(2026,6,1)],
            "2026-01-01","2026-04-01"
        )

    def test_training_on_calibration_quarter_rejected(self):
        with self.assertRaisesRegex(ValueError,"Temporal boundary"):
            validate_temporal([dt.date(2026,1,1)],
                [dt.date(2026,1,2)],[dt.date(2026,4,1)],
                "2026-01-01","2026-04-01")

    def test_calibration_on_test_day_rejected(self):
        with self.assertRaisesRegex(ValueError,"Temporal boundary"):
            validate_temporal([dt.date(2025,12,30)],
                [dt.date(2026,4,1)],[dt.date(2026,4,1)],
                "2026-01-01","2026-04-01")

    def test_no_empty_training_period(self):
        with self.assertRaisesRegex(ValueError,"Empty train"):
            validate_temporal([],[dt.date(2026,3,1)],
                [dt.date(2026,4,1)],"2026-01-01","2026-04-01")

    def test_not_using_fighter_outcome_or_bookmaker_prices(self):
        from scripts.precision_lab import FEATURES,RATINGS
        banned=("outcome","winner","red_odds","blue_odds","open_odds",
                "fighter_id","r_name","b_name","odds","future")
        self.assertTrue(all(k not in FEATURES+RATINGS for k in banned))


if __name__=="__main__":
    unittest.main()
