"""Synthetic-only Monte Carlo reproducibility and bankroll accounting tests."""
import copy
import json
import unittest
from pathlib import Path
from scripts.uf1cash_simulation_lab import run

ROOT=Path(__file__).resolve().parents[1]
def fixture():
    return (
        json.loads((ROOT/"research/uf1cash-synthetic-risk-scenarios-v1.json").read_text()),
        json.loads((ROOT/"public/uf1cash-status.json").read_text()),
        json.loads((ROOT/"records/uf1cash/challenge-policy-v3.json").read_text())
    )
def only(scenario):
    input,w,p=fixture()
    input["rounds"]=[{"roundId":"one-hypothetical-round",
      "tickets":[{"ticketId":"virtual-ticket","sport":"UFC","weight":"1"}],
      "jointScenarios":[{"label":"ONLY","probability":"1",
        "grossPayoutMultipliers":{"virtual-ticket":str(scenario)}}]}]
    input["trialCount"]=100
    return input,w,p

class SimulationTests(unittest.TestCase):
    def test_sample_simulation_is_reproducible(self):
        a,b,c=fixture();a["trialCount"]=250
        first=run(a,b,c);second=run(a,b,c)
        self.assertEqual(first,second)
        self.assertEqual(first["trialCount"],250)
    def test_100_percent_all_in_full_loss_is_ruin(self):
        a,b,c=only("0")
        result=run(a,b,c)
        self.assertEqual(result["ruinCount"],100)
        self.assertEqual(result["ruinPercent"],"100.00")
        self.assertEqual(result["medianFinalVirtualZAR"],"0.00")
    def test_100_percent_all_in_full_void_survives(self):
        a,b,c=only("1")
        result=run(a,b,c)
        self.assertEqual(result["ruinCount"],0)
        self.assertEqual(result["medianFinalVirtualZAR"],"3071.74")
        self.assertEqual(result["reachedGoalCount"],0)
    def test_10x_payout_crosses_target_and_stops(self):
        a,b,c=only("10")
        result=run(a,b,c)
        self.assertEqual(result["reachedGoalCount"],100)
        self.assertEqual(result["reachedGoalPercent"],"100.00")
        self.assertEqual(result["medianFinalVirtualZAR"],"30717.40")
    def test_sequential_goals_stop_before_next_round(self):
        a,b,c=only("2")
        r=a["rounds"][0]
        a["rounds"]=[dict(r,roundId=f"r-{i}") for i in range(1,7)]
        result=run(a,b,c)
        self.assertEqual(result["reachedGoalCount"],100)
        self.assertEqual(result["averageRoundsPlayed"],"4.00")
        self.assertEqual(result["medianFinalVirtualZAR"],"49147.84")
        self.assertEqual(result["observedSyntheticScenarioCounts"]["r-5"]["ONLY"],0)
    def test_no_unapproved_money_funding(self):
        a,b,c=fixture();a["startingBalanceZAR"]="3571.74"
        with self.assertRaisesRegex(ValueError,"current virtual wallet"):run(a,b,c)
    def test_missing_500_locked_out(self):
        a,b,c=only("1")
        result=run(a,b,c)
        self.assertEqual(result["disputedHistoricalStakeExcludedZAR"],"500.00")
        self.assertEqual(result["originalAvailableVirtualZAR"],"3071.74")
    def test_cannot_change_target(self):
        a,b,c=fixture();a["targetBalanceZAR"]="10000.00"
        with self.assertRaisesRegex(ValueError,"locked R25k"):run(a,b,c)
    def test_not_actual_forecast(self):
        a,b,c=fixture();a["mode"]="LIVE_FORECAST"
        with self.assertRaisesRegex(ValueError,"synthetic"):run(a,b,c)
    def test_unapproved_sport(self):
        a,b,c=fixture();a["rounds"][0]["tickets"][0]["sport"]="FOOTBALL"
        with self.assertRaisesRegex(ValueError,"Unapproved"):run(a,b,c)
    def test_probabilities_must_sum_to_one(self):
        a,b,c=fixture();a["rounds"][0]["jointScenarios"][0]["probability"]="0.56"
        with self.assertRaisesRegex(ValueError,"exactly to one"):run(a,b,c)
    def test_no_silent_independence_assumption(self):
        a,b,c=fixture()
        a["rounds"][0]["tickets"].append({"ticketId":"second-ticket","sport":"UFC","weight":"1"})
        with self.assertRaisesRegex(ValueError,"every ticket exactly once"):run(a,b,c)
    def test_joint_scenarios_can_define_correlated_multi_market(self):
        a,b,c=fixture()
        a["rounds"]=[{"roundId":"two-market-same-event",
          "tickets":[{"ticketId":"a","sport":"UFC","weight":"1"},
                     {"ticketId":"b","sport":"UFC","weight":"1"}],
          "jointScenarios":[
           {"label":"BOTH_WIN","probability":"0.30","grossPayoutMultipliers":{"a":"2","b":"2"}},
           {"label":"A_ONLY","probability":"0.25","grossPayoutMultipliers":{"a":"2","b":"0"}},
           {"label":"B_ONLY","probability":"0.25","grossPayoutMultipliers":{"a":"0","b":"2"}},
           {"label":"NEITHER","probability":"0.20","grossPayoutMultipliers":{"a":"0","b":"0"}}
          ]}]
        a["trialCount"]=1000
        result=run(a,b,c)
        self.assertEqual(result["trialCount"],1000)
        self.assertEqual(result["ruinCount"],result["observedSyntheticScenarioCounts"]["two-market-same-event"]["NEITHER"])
        self.assertTrue(result["averageFinalVirtualZAR"])
        self.assertEqual(result["noAuthoritativeWalletMutation"],True)
    def test_duplicate_ticket_id_refused(self):
        a,b,c=fixture()
        a["rounds"][0]["tickets"].append(copy.deepcopy(a["rounds"][0]["tickets"][0]))
        with self.assertRaisesRegex(ValueError,"Duplicate"):run(a,b,c)
    def test_more_than_hundred_thousand_trials_blocked(self):
        a,b,c=fixture();a["trialCount"]=100001
        with self.assertRaisesRegex(ValueError,"trial count"):run(a,b,c)
    def test_bad_seed_refused(self):
        a,b,c=fixture();a["seed"]=True
        with self.assertRaisesRegex(ValueError,"seed"):run(a,b,c)
    def test_invalid_multiplier_blocked(self):
        a,b,c=fixture();x=a["rounds"][0]
        x["jointScenarios"][0]["grossPayoutMultipliers"][x["tickets"][0]["ticketId"]]="-3"
        with self.assertRaisesRegex(ValueError,"multiplier"):run(a,b,c)
    def test_no_mutation_of_source_wallet(self):
        a,b,c=fixture()
        w=copy.deepcopy(b);p=copy.deepcopy(c)
        result=run(a,b,c)
        self.assertEqual(b,w);self.assertEqual(c,p)
        self.assertFalse(result["actualProfitEstablished"])
        self.assertTrue(result["noRealBets"])
        self.assertTrue(result["noActualForwardVirtualTicketsCreated"])
    def test_all_scenarios_account_for_every_trial(self):
        a,b,c=fixture();a["trialCount"]=1000
        result=run(a,b,c)
        self.assertEqual(result["ruinCount"]+result["reachedGoalCount"]+result["survivingBelowGoalCount"],1000)
    def test_repeat_a_new_round_even_on_same_sport_is_not_market_proof(self):
        a,b,c=fixture();a["trialCount"]=100
        result=run(a,b,c)
        self.assertEqual(result["mode"],"SYNTHETIC_ONLY")
        self.assertFalse(result["actualProfitEstablished"])

if __name__=="__main__":
    unittest.main()
