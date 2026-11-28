import unittest
from scripts.uf1cash_dataset_integrity import manifest

CUT=("2025-02-01T00:00:00Z","2025-03-01T00:00:00Z","2025-04-01T00:00:00Z")
def rows():
    return [{"sport":"UFC","eventId":str(i),"recordId":"r","featuresAt":f"2025-0{i}-01T00:00:00Z","startsAt":f"2025-0{i}-02T00:00:00Z","resultAt":f"2025-0{i}-03T00:00:00Z","features":{"rating":1500},"outcome":1} for i in range(1,4)]

class DatasetIntegrityTests(unittest.TestCase):
    def test_order_invariance(self):
        r=rows()
        self.assertEqual(manifest(r,*CUT),manifest(r[::-1],*CUT))
    def test_feature_change(self):
        r=rows()
        a=manifest(r,*CUT)
        r[0]["features"]["rating"]=1501
        b=manifest(r,*CUT)
        self.assertNotEqual(a["datasetSha256"],b["datasetSha256"])
        self.assertEqual(a["timestampManifestSha256"],b["timestampManifestSha256"])
        self.assertEqual(a["partitionContent"]["holdout"],b["partitionContent"]["holdout"])
    def test_outcome_change(self):
        r=rows()
        a=manifest(r,*CUT)
        r[2]["outcome"]=0
        self.assertNotEqual(a["partitionContent"]["holdout"],manifest(r,*CUT)["partitionContent"]["holdout"])
    def test_nonfinite(self):
        r=rows()
        r[0]["features"]["rating"]=float("nan")
        with self.assertRaisesRegex(ValueError,"finite JSON"):
            manifest(r,*CUT)
    def test_no_authentication_claim(self):
        a=manifest(rows(),*CUT)
        self.assertFalse(a["sourceAuthenticated"])
        self.assertFalse(a["walletMutated"])
        self.assertFalse(a["modelTrained"])
    def test_counts(self):
        a=manifest(rows(),*CUT)
        self.assertEqual({k:v["rows"] for k,v in a["partitionContent"].items()},{"train":1,"calibration":1,"holdout":1,"excluded":0})
