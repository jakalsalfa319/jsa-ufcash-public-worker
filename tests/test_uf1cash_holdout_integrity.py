import unittest
from scripts.uf1cash_holdout_integrity import validate

CUT=("2025-02-01T00:00:00Z","2025-03-01T00:00:00Z","2025-04-01T00:00:00Z")
def row(event,month,record="one"):
    return {"sport":"UFC","eventId":event,"recordId":record,
            "featuresAt":f"2025-{month}-02T00:00:00Z",
            "startsAt":f"2025-{month}-03T00:00:00Z",
            "resultAt":f"2025-{month}-04T00:00:00Z"}
def fixture():
    return [row("train","01"),row("cal","02"),row("test","03")]
class HoldoutTests(unittest.TestCase):
    def test_three_partitions(self):
        r=validate(fixture(),*CUT)
        self.assertEqual(r["eventCounts"],{"train":1,"calibration":1,"holdout":1,"excluded":0})
        self.assertFalse(r["walletMutated"])
    def test_duplicate(self):
        rows=fixture()
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            validate(rows+[rows[0]],*CUT)
    def test_features_after_start(self):
        rows=fixture()
        rows[0]["featuresAt"]=rows[0]["resultAt"]
        with self.assertRaisesRegex(ValueError,"chronology"):
            validate(rows,*CUT)
    def test_late_labels_excluded(self):
        rows=fixture()
        extra=row("late","01")
        extra["resultAt"]="2025-02-02T00:00:00Z"
        r=validate(rows+[extra],*CUT)
        self.assertEqual(r["eventCounts"]["excluded"],1)
    def test_grouped_event(self):
        r=validate(fixture()+[row("test","03","two")],*CUT)
        self.assertEqual(r["eventCounts"]["holdout"],1)
        self.assertEqual(r["partitions"]["holdout"][0]["recordIds"],["one","two"])
    def test_inconsistent_start(self):
        with self.assertRaisesRegex(ValueError,"Inconsistent"):
            validate(fixture()+[row("test","02","two")],*CUT)
    def test_bad_cutoff(self):
        with self.assertRaisesRegex(ValueError,"Cutoffs"):
            validate(fixture(),CUT[1],CUT[0],CUT[2])
    def test_missing_partition(self):
        with self.assertRaisesRegex(ValueError,"three partitions"):
            validate(fixture()[:2],*CUT)
    def test_missing_timezone(self):
        rows=fixture()
        rows[0]["featuresAt"]="2025-01-02T00:00:00"
        with self.assertRaisesRegex(ValueError,"Timezone"):
            validate(rows,*CUT)
