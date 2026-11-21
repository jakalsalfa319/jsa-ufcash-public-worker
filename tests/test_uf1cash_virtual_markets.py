"""UF1Cash multi-market virtual receipts use synthetic odds, not real bets."""
import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from scripts.all_in_challenge import cents
from scripts.uf1cash_virtual_markets import freeze,reconcile

ROOT=Path(__file__).resolve().parents[1]
NOW=datetime(2026,12,1,10,0,tzinfo=timezone.utc)
AFTER=datetime(2026,12,2,10,0,tzinfo=timezone.utc)

def wallet_policy():
    return (
       json.loads((ROOT/"public/uf1cash-status.json").read_text()),
       json.loads((ROOT/"records/uf1cash/challenge-policy-v3.json").read_text())
    )

def ticket(tid="test-ticket-1",market="MONEYLINE",grading="FIXED_BINARY",
           sport="UFC",event="synthetic-match",weight=1):
    return {"ticketId":tid,"sourceEventId":event,
      "sport":sport,"marketType":market,"selection":"Synthetic contender",
      "eventStartsUTC":"2026-12-01T18:00:00Z",
      "modelPSelection":"0.58","weight":weight,
      "quote":{"decimalOdds":"2.10","sourceUrl":"https://example.test/quotes/sample",
               "sourceName":"SYNTHETIC TEST ONLY","capturedAtUTC":"2026-12-01T09:45:00Z"},
      "settlementContract":{"grading":grading,
         "publishedRulesUrl":"https://example.test/rules/mock",
         "specificTerms":"Full stake multiplied by fixed decimal odds on WIN; zero on LOSS; original stake refunded on VOID.",
         "supportsVoidRefund":True}}

def data(tickets,stake="3071.74",strategy="BASKET"):
    return {"schema":"UF1CASH_MULTI_MARKET_INPUT_V1",
      "roundId":"test-virtual-market-round","strategy":strategy,
      "availableBankrollZAR":stake,"modelCapturedUTC":"2026-12-01T09:30:00Z",
      "modelSourceUrl":"https://example.test/model/frozen",
      "modelSha256":"a"*64,"minEstimatedEV":"0.03",
      "tickets":tickets}

def run(items,stake="3071.74",strategy="BASKET"):
    wallet,policy=wallet_policy()
    return freeze(wallet,policy,data(items,stake,strategy),NOW)

def outcome(ticketid,state="WIN"):
    return {"ticketId":ticketid,"status":state,
       "observedAtUTC":"2026-12-01T21:00:00Z",
       "sourceUrl":"https://example.test/results/mock"}

class MultiMarketTests(unittest.TestCase):
    def test_full_current_wallet_single_market(self):
        r=run([ticket()])
        self.assertEqual(r["allInDeployedZAR"],"3071.74")
        self.assertEqual(r["uncommittedZAR"],"0.00")
        self.assertFalse(r["bookmakerExecuted"])
    def test_multiple_markets_same_event_are_distinct_tickets(self):
        r=run([ticket("win"),ticket("totals","TOTALS_OVER_UNDER",event="synthetic-match",weight=2),
               ticket("method","METHOD_OF_VICTORY",event="synthetic-match",weight=3)])
        self.assertEqual(len(r["frozenReceipt"]["selections"]),3)
        self.assertEqual(sum(cents(s["stakeZAR"]) for s in r["frozenReceipt"]["selections"]),307174)
        self.assertEqual({x["sourceEventId"] for x in r["tickets"]},{"synthetic-match"})
    def test_weights_discretionary_not_research_percentage(self):
        r=run([ticket("horse-market",market="HORSE_PLACE_FIXED",sport="HORSE_RACING")])
        self.assertEqual(r["allInDeployedZAR"],"3071.74")
        self.assertEqual(r["tickets"][0]["sport"],"HORSE_RACING")
    def test_manual_market_allowed_but_cannot_auto_settle(self):
        r=run([ticket(market="EACH_WAY",grading="MANUAL_REVIEW")])
        x=reconcile(r,[],AFTER)
        self.assertEqual(x["availableReportedPayoutZAR"],"0.00")
        self.assertEqual(x["lockedUnresolvedStakeZAR"],"3071.74")
        with self.assertRaisesRegex(ValueError,"cannot automatically credit"):
            reconcile(r,[outcome("test-ticket-1")],AFTER)
    def test_unknown_custom_market_must_be_manual(self):
        with self.assertRaisesRegex(ValueError,"MANUAL_REVIEW"):
            run([ticket(market="EXOTIC_SPECIAL")])
        r=run([ticket(market="EXOTIC_SPECIAL",grading="MANUAL_REVIEW")])
        self.assertEqual(r["tickets"][0]["grading"],"MANUAL_REVIEW")
    def test_accumulator_requires_real_combined_quote(self):
        x=ticket(market="ACCUMULATOR",grading="MANUAL_REVIEW")
        x["legs"]=[
           {"sourceEventId":"first-match","marketType":"MONEYLINE",
            "selection":"fighter A","eventStartsUTC":"2026-12-01T18:00:00Z"},
           {"sourceEventId":"second-match","marketType":"MONEYLINE",
            "selection":"driver B","eventStartsUTC":"2026-12-01T20:00:00Z"}]
        with self.assertRaisesRegex(ValueError,"genuinely offered"):run([x])
        x["quote"]["offeredCombinedPrice"]=True
        with self.assertRaisesRegex(ValueError,"joint model"):run([x])
        x["jointProbabilityModelUrl"]="https://example.test/model/joint"
        r=run([x])
        self.assertEqual(r["allInDeployedZAR"],"3071.74")
        self.assertEqual(len(r["tickets"][0]["legs"]),2)
    def test_accumulator_blocks_leg_already_started(self):
        x=ticket(market="ACCUMULATOR",grading="MANUAL_REVIEW")
        x["quote"]["offeredCombinedPrice"]=True
        x["jointProbabilityModelUrl"]="https://example.test/model/joint"
        x["legs"]=[
           {"sourceEventId":"first","marketType":"MONEYLINE",
            "selection":"A","eventStartsUTC":"2026-12-01T08:00:00Z"},
           {"sourceEventId":"second","marketType":"MONEYLINE",
            "selection":"B","eventStartsUTC":"2026-12-01T19:00:00Z"}]
        with self.assertRaisesRegex(ValueError,"earliest leg"):run([x])
    def test_duplicate_ticket_ids_rejected(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):run([ticket(),ticket()])
    def test_locked_historical_pending_stake_not_spent(self):
        with self.assertRaisesRegex(ValueError,"current wallet"):run([ticket()],stake="3571.74")
    def test_previous_original_balance_not_spent(self):
        with self.assertRaisesRegex(ValueError,"current wallet"):run([ticket()],stake="2000.00")
    def test_unknown_sport_rejected(self):
        with self.assertRaisesRegex(ValueError,"Unapproved sport"):
            run([ticket(sport="TENNIS")])
    def test_invalid_market_rules_rejected(self):
        x=ticket();x["settlementContract"]["publishedRulesUrl"]="http://example.test/rules"
        with self.assertRaisesRegex(ValueError,"rules HTTPS"):run([x])
    def test_unsafe_auto_settlement_market_rejected(self):
        with self.assertRaisesRegex(ValueError,"MANUAL_REVIEW"):
            run([ticket(market="EACH_WAY",grading="FIXED_BINARY")])
    def test_no_quote_abstains_in_legacy_but_contract_requires_quote(self):
        x=ticket();x["quote"]=None
        with self.assertRaisesRegex(ValueError,"Quoted fixed"):run([x])
    def test_stale_quote_abstains(self):
        x=ticket();x["quote"]["capturedAtUTC"]="2026-12-01T06:00:00Z"
        y=data([x]);y["modelCapturedUTC"]="2026-12-01T05:30:00Z"
        wallet,policy=wallet_policy()
        r=freeze(wallet,policy,y,NOW)
        self.assertEqual(r["allInDeployedZAR"],"0.00")
        self.assertEqual(r["uncommittedZAR"],"3071.74")
    def test_reported_full_win_provisional(self):
        r=run([ticket()])
        x=reconcile(r,[outcome("test-ticket-1")],AFTER)
        self.assertEqual(x["availableReportedPayoutZAR"],"6450.65")
        self.assertFalse(x["independentResultVerification"])
        self.assertEqual(x["realBetsPlaced"],0)
    def test_void_refund(self):
        r=run([ticket()])
        x=reconcile(r,[outcome("test-ticket-1","VOID")],AFTER)
        self.assertEqual(x["voidRefundsZAR"],"3071.74")
    def test_partially_paid_while_other_ticket_pending(self):
        r=run([ticket("one"),ticket("two",event="event-two")])
        x=reconcile(r,[outcome("one")],AFTER)
        self.assertEqual(x["availableReportedPayoutZAR"],"3225.33")
        self.assertEqual(x["lockedUnresolvedStakeZAR"],"1535.87")
    def test_tampered_receipt_rejected(self):
        r=run([ticket()])
        r["tickets"][0]["specificTerms"]="bad modification"
        with self.assertRaisesRegex(ValueError,"Tampered"):reconcile(r,[],AFTER)
    def test_duplicate_result_not_counted_twice(self):
        r=run([ticket()])
        with self.assertRaisesRegex(ValueError,"duplicate"):
            reconcile(r,[outcome("test-ticket-1")]*2,AFTER)
    def test_result_before_event_rejected(self):
        r=run([ticket()])
        x=outcome("test-ticket-1");x["observedAtUTC"]="2026-12-01T16:00:00Z"
        with self.assertRaisesRegex(ValueError,"outside permissible"):
            reconcile(r,[x],AFTER)

if __name__=="__main__":unittest.main()
