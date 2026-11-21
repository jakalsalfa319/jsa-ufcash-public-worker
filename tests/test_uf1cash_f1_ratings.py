"""F1 Elo chronology and source-structure tests, all test results fictional."""
import copy
import json
import math
import unittest
from scripts.uf1cash_f1_ratings import from_payloads,evaluate,win_probs,update,UTC

def race(year,round_id,day,who="driver_a"):
    entrants=[
      {"Driver":{"driverId":"driver_a"},"position":"1" if who=="driver_a" else "2","grid":"1"},
      {"Driver":{"driverId":"driver_b"},"position":"1" if who=="driver_b" else "2","grid":"2"}]
    return {"season":str(year),"round":str(round_id),"raceName":"Synthetic Race",
            "date":day,"time":"12:00:00Z","Results":entrants}

def package(*rows):
    return {"MRData":{"RaceTable":{"Races":list(rows)}}}

class F1ModelTests(unittest.TestCase):
    def test_only_past_races_used(self):
        a=package(race(2025,1,"2025-01-05"),race(2025,2,"2025-01-12"),
                  race(2026,1,"2026-11-29"))
        r=from_payloads([a],"2026-11-22T12:00:00Z")
        self.assertEqual(len(r),2)
        self.assertEqual(r[-1]["round"],"2")
    def test_no_event_at_cutoff(self):
        a=package(race(2026,1,"2026-11-22"))
        self.assertEqual(from_payloads([a],"2026-11-22T12:00:00Z"),[])
    def test_rejects_duplicate_event_across_payloads(self):
        a=package(race(2025,1,"2025-01-05"))
        with self.assertRaisesRegex(ValueError,"Duplicated"):
            from_payloads([a,a],"2026-11-22T12:00:00Z")
    def test_invalid_driver_rejected(self):
        a=package(race(2025,1,"2025-01-05"))
        a["MRData"]["RaceTable"]["Races"][0]["Results"][1]["Driver"]["driverId"]="driver_a"
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            from_payloads([a],"2026-11-22T12:00:00Z")
    def test_online_update_conserves_ratings(self):
        ratings={"driver_a":1500.0,"driver_b":1500.0}
        initial=sum(ratings.values())
        update(ratings,[{"id":"driver_a","position":1,"grid":2},
                        {"id":"driver_b","position":2,"grid":1}])
        self.assertGreater(ratings["driver_a"],ratings["driver_b"])
        self.assertAlmostEqual(sum(ratings.values()),initial)
    def test_probabilities_sum_to_one(self):
        p=win_probs([{"id":"a","grid":1},{"id":"b","grid":2},{"id":"c","grid":3}],{})
        self.assertAlmostEqual(sum(p.values()),1.0)
        self.assertGreater(p["a"],p["b"])
    def test_no_lookahead_in_elo_rating(self):
        past=package(race(2025,1,"2025-01-05",who="driver_a"))
        future=package(race(2026,1,"2026-11-29",who="driver_b"))
        one=evaluate([past],"2026-11-22T12:00:00Z")
        two=evaluate([past,future],"2026-11-22T12:00:00Z")
        self.assertEqual(one,two)
    def test_backtest_metrics_pole_baseline(self):
        a=package(race(2025,1,"2025-01-05",who="driver_a"),
                  race(2025,2,"2025-01-12",who="driver_b"))
        r=evaluate([a],"2026-11-22T12:00:00Z")
        self.assertEqual(r["historicalRacesProcessed"],2)
        self.assertEqual(r["poleSitterWinnerBaseline"],0.5)
        self.assertIsNone(r["futureRaceModelProbability"])
        self.assertFalse(r["paperBetEligible"])
        self.assertEqual(r["newPaperBets"],0)
        self.assertEqual(r["realBets"],0)
    def test_invalid_tz_refused(self):
        with self.assertRaisesRegex(ValueError,"Timezone"):
            evaluate([],"2026-11-22T12:00:00")
    def test_empty_dataset_no_fake_accuracy(self):
        a=evaluate([package()],"2026-11-22T12:00:00Z")
        self.assertIsNone(a["walkforwardTopOneAccuracy"])
        self.assertIsNone(a["latestHistoricalRaceDate"])
    def test_zero_grid_is_allowed_in_historical_data(self):
        a=package(race(2025,1,"2025-01-05"))
        a["MRData"]["RaceTable"]["Races"][0]["Results"][0]["grid"]="0"
        self.assertEqual(len(from_payloads([a],"2026-11-22T12:00:00Z")),1)

if __name__=="__main__":unittest.main()
