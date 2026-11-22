"""Forecast skill: strict source chronology, final settlement and proper scores."""
import copy
import math
import unittest
from datetime import datetime,timezone
from scripts.uf1cash_forecast_skill import audit

NOW=datetime(2026,11,22,12,tzinfo=timezone.utc)
def entry(eid="test-event-1",sport="UFC",p="0.60",y=1,baseline="0.50"):
    return {"eventId":eid,"marketId":"winner","selectionId":"fictional-selection",
     "sport":sport,"predictedAtUTC":"2026-11-20T10:00:00Z",
     "eventStartsUTC":"2026-11-21T18:00:00Z",
     "resultObservedUTC":"2026-11-21T22:00:00Z",
     "modelSnapshotUrl":"https://example.test/frozen/model",
     "modelSha256":"e"*64,"resultSourceUrl":"https://example.test/verified/results",
     "resultStatus":"FINAL_REVIEWED","modelProbability":p,"outcome":y,
     "baselineProbability":baseline}
def data(*rows):
    return {"schema":"UF1CASH_BINARY_FORECAST_AUDIT_INPUT_V1",
     "records":list(rows)}
class AuditTests(unittest.TestCase):
    def test_binary_brier_logloss(self):
        r=audit(data(entry(),entry("test-event-2",p="0.80",y=0)),NOW)
        self.assertEqual(r["skill"]["count"],2)
        self.assertEqual(r["skill"]["meanBrierLoss"],0.4)
        self.assertAlmostEqual(r["skill"]["meanLogLoss"],(-math.log(.6)-math.log(.2))/2,places=5)
        self.assertFalse(r["profitableBettingEdgeEstablished"])
    def test_base_rate_and_calibration_bins(self):
        r=audit(data(entry("a",p="0.60",y=1),entry("b",p="0.60",y=0)),NOW)
        self.assertEqual(r["skill"]["baseRate"],0.5)
        self.assertAlmostEqual(r["skill"]["expectedCalibrationError"],0.1)
        self.assertEqual(r["skill"]["baselineMatchedCount"],2)
    def test_no_future_information_leak(self):
        x=entry();x["predictedAtUTC"]="2026-11-21T19:00:00Z"
        with self.assertRaisesRegex(ValueError,"LOOKAHEAD_BLOCKED"):audit(data(x),NOW)
    def test_post_event_results_only(self):
        x=entry();x["resultObservedUTC"]="2026-11-21T16:00:00Z"
        with self.assertRaisesRegex(ValueError,"LOOKAHEAD_BLOCKED"):audit(data(x),NOW)
    def test_no_results_from_future(self):
        x=entry();x["resultObservedUTC"]="2026-11-23T16:00:00Z"
        with self.assertRaisesRegex(ValueError,"LOOKAHEAD_BLOCKED"):audit(data(x),NOW)
    def test_disputed_not_scored_even_if_outcome_filled(self):
        x=entry();x["resultStatus"]="DISPUTED"
        with self.assertRaisesRegex(ValueError,"final reviewed"):audit(data(x),NOW)
    def test_pending_not_scored(self):
        x=entry();x["resultStatus"]="PENDING"
        with self.assertRaisesRegex(ValueError,"final reviewed"):audit(data(x),NOW)
    def test_missing_result_source_rejected(self):
        x=entry();x["resultSourceUrl"]=None
        with self.assertRaisesRegex(ValueError,"Source-linked"):audit(data(x),NOW)
    def test_sha_required(self):
        x=entry();x["modelSha256"]="a"
        with self.assertRaisesRegex(ValueError,"SHA"):audit(data(x),NOW)
    def test_invalid_probability(self):
        x=entry();x["modelProbability"]="1.2"
        with self.assertRaisesRegex(ValueError,"between 0 and 1"):audit(data(x),NOW)
    def test_false_truth_bool_rejected(self):
        x=entry();x["outcome"]=True
        with self.assertRaisesRegex(ValueError,"definite"):audit(data(x),NOW)
    def test_duplicate_event_market_selection_rejected(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            audit(data(entry(),entry()),NOW)
    def test_group_sport_metrics(self):
        r=audit(data(entry("ufc"),entry("f1",sport="F1",y=0)),NOW)
        self.assertEqual(r["bySport"]["UFC"]["count"],1)
        self.assertEqual(r["bySport"]["F1"]["count"],1)
        self.assertIsNone(r["bySport"]["CRICKET"])
        self.assertEqual(r["skill"]["uniqueUnderlyingEvents"],2)
    def test_missing_baseline_is_explicit(self):
        r=audit(data(entry(baseline=None)),NOW)
        self.assertEqual(r["skill"]["baselineMatchedCount"],0)
        self.assertIsNone(r["skill"]["baselineBrierLossOnAvailableMatchedRows"])
    def test_no_actual_profit_claim(self):
        r=audit(data(entry()),NOW)
        self.assertFalse(r["sourceEvidenceIndependentlyAuthenticated"])
        self.assertEqual(r["realBetsPlaced"],0)
        self.assertFalse(r["profitableBettingEdgeEstablished"])
    def test_outcome_cannot_be_none(self):
        x=entry();x["outcome"]=None
        with self.assertRaisesRegex(ValueError,"definite"):audit(data(x),NOW)
    def test_no_side_effects(self):
        x=data(entry())
        before=copy.deepcopy(x)
        audit(x,NOW)
        self.assertEqual(x,before)

if __name__=="__main__":unittest.main()
