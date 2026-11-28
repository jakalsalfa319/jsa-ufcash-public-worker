import unittest
from scripts.uf1cash_forecast_skill import _paired_baseline, _metrics

class PairedBaselineTests(unittest.TestCase):
    def test_missing_baseline_not_compared(self):
        self.assertIsNone(_paired_baseline([(0.9,1,None,"a")]))
    def test_matched_cohort_only(self):
        r=_metrics([(0.9,0,None,"a"),(0.8,1,0.5,"b")])
        p=r["pairedBaselineComparison"]
        self.assertEqual(p["matchedRows"],1)
        self.assertEqual(p["modelBrier"],0.04)
        self.assertEqual(p["baselineBrier"],0.25)
        self.assertEqual(p["pairedDifference"],-0.21)
    def test_correlated_rows_do_not_inflate_events(self):
        r=_paired_baseline([(0.7,1,0.5,"same")]*100)
        self.assertEqual(r["matchedEvents"],1)
        self.assertIsNone(r["eventBootstrap95Interval"])
    def test_seeded_interval(self):
        rows=[(0.8,1,0.5,str(i)) for i in range(12)]
        a=_paired_baseline(rows)
        self.assertEqual(a,_paired_baseline(rows))
        self.assertEqual(a["eventBootstrap95Interval"],[-0.21,-0.21])
    def test_no_superiority_claim(self):
        r=_paired_baseline([(0.2,1,0.5,"a")])
        self.assertGreater(r["pairedDifference"],0)
        self.assertFalse(r["baselineProvenanceIndependentlyVerified"])
