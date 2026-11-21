"""Synthetic source structures only. No real betting instructions."""
import copy
import unittest
from unittest.mock import patch
from scripts.uf1cash_openf1_freshness import historical_race,results_summary,inspect

NOW="2026-11-22T12:00:00Z"
def session(key=2026,ends="2026-11-20T16:00:00Z",cancelled=False):
    return {"session_key":key,"session_type":"Race","date_start":"2026-11-20T14:00:00Z",
       "date_end":ends,"is_cancelled":cancelled,"location":"Synthetic Grand Prix",
       "session_name":"Race"}
def finish(key=2026):
    return [{"session_key":key,"driver_number":i,"position":i,
       "dnf":False,"dns":False,"dsq":False} for i in range(1,21)]
class OpenF1Tests(unittest.TestCase):
    def test_latest_completed_race_chosen(self):
        r=historical_race([session(3,"2026-11-20T16:00:00Z"),
                           session(2,"2026-11-19T16:00:00Z")],NOW)
        self.assertEqual(r["session_key"],3)
    def test_future_race_never_included(self):
        self.assertIsNone(historical_race([session(3,"2026-11-23T16:00:00Z")],NOW))
    def test_live_race_never_included(self):
        self.assertIsNone(historical_race([session(3,"2026-11-22T11:45:00Z")],NOW))
    def test_cancelled_event_skipped(self):
        self.assertIsNone(historical_race([session(cancelled=True)],NOW))
    def test_finished_source_is_recent(self):
        r=results_summary(finish(),session(),NOW)
        self.assertEqual(r["freshnessStatus"],"RECENT_WITHIN_30_DAYS")
        self.assertEqual(r["reportedWinnerDriverNumber"],1)
        self.assertEqual(r["classifications"],20)
        self.assertFalse(r["paperBetEligible"])
    def test_old_results_flagged_stale(self):
        r=results_summary(finish(),session(ends="2026-05-24T20:00:00Z"),NOW)
        self.assertEqual(r["freshnessStatus"],"STALE_OVER_30_DAYS")
        self.assertGreater(r["daysSinceLatestCompletedRace"],150)
    def test_missing_winner_refused(self):
        r=finish();r[0]["position"]=30
        with self.assertRaisesRegex(ValueError,"Insufficient"):results_summary(r,session(),NOW)
    def test_duplicate_driver_refused(self):
        r=finish();r[1]["driver_number"]=1
        with self.assertRaisesRegex(ValueError,"Duplicated"):results_summary(r,session(),NOW)
    def test_other_session_results_rejected(self):
        r=finish();r[0]["session_key"]=555
        with self.assertRaisesRegex(ValueError,"Wrong results"):results_summary(r,session(),NOW)
    def test_not_full_classification_refused(self):
        with self.assertRaisesRegex(ValueError,"Insufficient"):results_summary(finish()[:5],session(),NOW)
    def test_no_race_means_no_bet(self):
        with patch("scripts.uf1cash_openf1_freshness.fetch_json",return_value=[]):
            r=inspect(2026,NOW)
        self.assertEqual(r["freshnessStatus"],"NO_COMPLETED_RACE")
        self.assertFalse(r["paperBetEligible"])
    def test_only_two_api_calls_when_valid(self):
        with patch("scripts.uf1cash_openf1_freshness.fetch_json",side_effect=[[session()],finish()]) as f:
            r=inspect(2026,NOW)
        self.assertEqual(f.call_count,2)
        self.assertEqual(r["virtualBets"],0)
        self.assertEqual(r["realBets"],0)
    def test_no_future_bet_even_if_source_recent(self):
        r=results_summary(finish(),session(),NOW)
        self.assertIsNone(r["forecastProbability"])
        self.assertIsNone(r["bettableOdds"])
        self.assertFalse(r["independentlyCrossCheckedWithOfficialF1"])

if __name__=="__main__":unittest.main()
