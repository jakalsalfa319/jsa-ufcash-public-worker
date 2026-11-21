"""Fictional R25k wallet rule tests, no bookmaker access."""
import copy
import json
import unittest
from datetime import datetime,timezone
from pathlib import Path
from scripts.all_in_challenge import cents
from scripts.uf1cash_challenge import status,prepare

BASE=Path(__file__).resolve().parents[1]
NOW=datetime(2026,11,25,12,tzinfo=timezone.utc)

def fixture():
    return (json.loads((BASE/"public/uf1cash-status.json").read_text()),
        json.loads((BASE/"records/uf1cash/challenge-policy-v3.json").read_text()))

def candidate(eid="test-ufc-1",sport="UFC",with_quote=True):
    return {"eventId":eid,"sport":sport,"market":"moneyline","selection":"Synthetic test fighter",
       "eventStartsUTC":"2026-11-25T18:00:00Z","modelPSelection":"0.62",
       "quote":{"sourceName":"unit-test synthetic price","sourceUrl":"https://example.org/mock/price",
          "capturedAtUTC":"2026-11-25T11:45:00Z","americanOdds":-110} if with_quote else None}

def round_input(strategy="SINGLE",candidates=None):
    return {"schema":"UFCASH_ALLIN_INPUT_V1","roundId":"synthetic-round-test",
       "strategy":strategy,"availableBankrollZAR":"3071.74","minEstimatedEV":"0.03",
       "modelSourceUrl":"https://example.org/mock/model.json",
       "modelSha256":"a"*64,"modelCapturedUTC":"2026-11-25T11:00:00Z",
       "candidates":candidates if candidates is not None else [candidate()]}

class GoalRulesTests(unittest.TestCase):
    def test_active_wallet_and_goal(self):
        r=status(*fixture())
        self.assertEqual(r["availableBalanceZAR"],"3071.74")
        self.assertEqual(r["lockedHistoricalPendingStakeZAR"],"500.00")
        self.assertEqual(r["toGoZAR"],"21928.26")
        self.assertEqual(r["progressPercent"],"12.29")
        self.assertFalse(r["strategyReplacementSuggestionAllowed"])
        self.assertEqual(r["developmentFocusPercent"], {"UFC":50,"F1":12.5,"RUGBY_UNION":12.5,"HORSE_RACING":12.5,"CRICKET":12.5})
    def test_one_selection_all_in(self):
        w,p=fixture()
        x=prepare(w,p,round_input(),NOW)["receipt"]
        self.assertEqual(x["deployedZAR"],"3071.74")
        self.assertEqual(x["uncommittedZAR"],"0.00")
        self.assertEqual(x["selections"][0]["stakeZAR"],"3071.74")
        self.assertEqual(x["realBetsPlaced"],0)
    def test_three_selection_basket_all_cents(self):
        w,p=fixture()
        a=[candidate("test-"+str(i),sport="F1" if i==1 else "UFC") for i in range(3)]
        x=prepare(w,p,round_input("BASKET",a),NOW)["receipt"]
        self.assertEqual(sum(cents(z["stakeZAR"]) for z in x["selections"]),307174)
        self.assertEqual(x["uncommittedZAR"],"0.00")
    def test_missing_quote_abstains_no_spend(self):
        w,p=fixture()
        x=prepare(w,p,round_input(candidates=[candidate(with_quote=False)]),NOW)["receipt"]
        self.assertEqual(x["status"],"ABSTAIN_NO_QUALIFIED_MARKET")
        self.assertEqual(x["uncommittedZAR"],"3071.74")
        self.assertEqual(x["deployedZAR"],"0.00")
    def test_old_balance_rejected(self):
        w,p=fixture();x=round_input();x["availableBankrollZAR"]="2000.00"
        with self.assertRaisesRegex(ValueError,"current wallet"):prepare(w,p,x,NOW)
    def test_locked_stake_cannot_be_reused(self):
        w,p=fixture();x=round_input();x["availableBankrollZAR"]="3571.74"
        with self.assertRaisesRegex(ValueError,"current wallet"):prepare(w,p,x,NOW)
    def test_other_sports_stay_on_bench(self):
        w,p=fixture()
        with self.assertRaisesRegex(ValueError,"Only UFC, F1, rugby union"):
            prepare(w,p,round_input(candidates=[candidate("tennis","TENNIS")]),NOW)
    def test_all_five_sports_eligible_together(self):
        w,p=fixture()
        sports=["UFC","F1","RUGBY_UNION","HORSE_RACING","CRICKET"]
        a=[candidate("test-"+str(i),sport=s) for i,s in enumerate(sports)]
        receipt=prepare(w,p,round_input("BASKET",a),NOW)["receipt"]
        self.assertEqual(len(receipt["selections"]),5)
        self.assertEqual(sum(cents(row["stakeZAR"]) for row in receipt["selections"]),307174)
        self.assertEqual(receipt["uncommittedZAR"],"0.00")
    def test_development_percent_is_not_forced_staking_percent(self):
        w,p=fixture()
        one=prepare(w,p,round_input(candidates=[candidate("horse","HORSE_RACING")]),NOW)["receipt"]
        self.assertEqual(one["selections"][0]["stakeZAR"],"3071.74")
    def test_value_gate_cannot_be_relaxed(self):
        w,p=fixture();x=round_input();x["minEstimatedEV"]="0.0"
        with self.assertRaisesRegex(ValueError,"lowered"):prepare(w,p,x,NOW)
    def test_target_threshold_lock(self):
        w,p=fixture();p["virtualGoalZAR"]="5000.00"
        with self.assertRaisesRegex(ValueError,"locked"):status(w,p)
        w,p=fixture();p["allInShareOfAvailableBalance"]="0.5"
        with self.assertRaisesRegex(ValueError,"100%"):status(w,p)
    def test_review_permitted_only_at_25000(self):
        w,p=fixture();w=copy.deepcopy(w)
        w["currentBalanceZAR"]=w["prospectiveWallet"]["balanceAvailableZAR"]="24999.99"
        r=status(w,p);self.assertFalse(r["strategyReplacementSuggestionAllowed"])
        self.assertEqual(r["toGoZAR"],"0.01")
        w["currentBalanceZAR"]=w["prospectiveWallet"]["balanceAvailableZAR"]="25000.00"
        r=status(w,p);self.assertTrue(r["strategyReplacementSuggestionAllowed"])
        self.assertFalse(r["automaticStrategySwitch"])
        self.assertTrue(r["strategyChangeRequiresApproval"])
    def test_bankrupt_wallet_cannot_stake(self):
        w,p=fixture();w=copy.deepcopy(w)
        w["currentBalanceZAR"]=w["prospectiveWallet"]["balanceAvailableZAR"]="0.00"
        self.assertEqual(status(w,p)["challengePhase"],"NO_AVAILABLE_CASH_RESULTS_PENDING")
        with self.assertRaisesRegex(ValueError,"No available"):prepare(w,p,round_input(),NOW)
    def test_policy_scope_lock(self):
        w,p=fixture();p["allowedSports"].append("BASKETBALL")
        with self.assertRaisesRegex(ValueError,"five approved sports"):status(w,p)
    def test_no_real_money(self):
        w,p=fixture();w=copy.deepcopy(w);w["prospectiveWallet"]["realFundsZAR"]="1.00"
        with self.assertRaisesRegex(ValueError,"top-ups"):status(w,p)
    def test_regenerated_snapshot_matches_public(self):
        r=status(*fixture())
        actual=json.loads((BASE/"public/uf1cash-goal.json").read_text())
        self.assertEqual(r,actual)

if __name__=="__main__":unittest.main()
