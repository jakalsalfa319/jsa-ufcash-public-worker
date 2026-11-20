import datetime as dt
import unittest
from scripts.card_integrity import PAIRS, EVENT_DATE
from scripts.settle_event_v2 import reconcile, score, wilson_lower, pair_key

AFTER=dt.datetime(2026,11,22,10,0,tzinfo=dt.timezone.utc)


def frozen():
    original={"schema":"JSA_EVENT_JOURNAL_V1","eventDate":EVENT_DATE,
       "status":"PRE_EVENT_RESEARCH_ONLY","generatedAtUTC":"2026-11-19T21:44:30Z",
       "snapshotSha256":"test-hash",
       "predictions":[{"red":a,"blue":b,"outcome":None,"betPlaced":False,
           "ufcashProbabilityRed":.65,"oddsFreeProbabilityRed":.6 if i<6 else None}
           for i,(a,b) in enumerate(PAIRS)]}
    latest={"schema":"JSA_FRONTIER_PROSPECTIVE_V2","eventDate":EVENT_DATE,
       "recordedAtUTC":"2026-11-20T14:41:29Z","sourceReportSha256":"test-run",
       "predictions":[{"fighterA":a,"fighterB":b,"outcome":None,"betPlaced":False,
           "redProbability":.7 if i<6 else None,"passesValidationLockedGate":i<2}
           for i,(a,b) in enumerate(PAIRS)]}
    return original,latest


def data(i,status="COMPLETED",winner="A"):
    a,b=PAIRS[i]
    return {"fighterA":a,"fighterB":b,"status":status,
      "winner":a if winner=="A" else b if winner=="B" else "",
      "source_url":"https://www.ufc.com/event/ufc-fight-night-november-21-2026" if status!="PENDING" else "",
      "verified_at_utc":"2026-11-22T08:00:00Z" if status!="PENDING" else ""}


class MultiModelSettlementTests(unittest.TestCase):
    def test_decisive_bouts_score_all_frozen_models(self):
        a,b=frozen()
        result=reconcile(a,b,[data(i,winner="A" if i%2==0 else "B") for i in range(7)],AFTER)
        self.assertEqual(result["decisiveScored"],7)
        self.assertEqual(result["scores"]["ufcash"]["eligible"],7)
        self.assertEqual(result["scores"]["oddsFree"]["eligible"],6)
        self.assertEqual(result["scores"]["frontier"]["eligible"],6)
        self.assertEqual(result["scores"]["frontierSelected"]["eligible"],2)
        self.assertFalse(result["automatedBets"])
        self.assertIsNone(result["financialROI"])
        self.assertFalse(result["accuracy99_9Verified"])
        self.assertIn("UNVERIFIED",result["status"])

    def test_cancelled_replaced_draw_and_nc_not_scored(self):
        a,b=frozen()
        rows=[data(0),data(1,"CANCELLED",""),data(2,"REPLACED",""),
              data(3,"DRAW",""),data(4,"NO_CONTEST",""),data(5,"POSTPONED",""),
              data(6,"PENDING","")]
        result=reconcile(a,b,rows,AFTER)
        self.assertEqual(result["decisiveScored"],1)
        self.assertEqual(result["scores"]["ufcash"]["eligible"],1)
        self.assertEqual(result["statusCounts"]["CANCELLED"],1)
        self.assertEqual(result["statusCounts"]["REPLACED"],1)
        self.assertEqual(result["statusCounts"]["PENDING"],1)

    def test_missing_bouts_default_pending_not_losses(self):
        a,b=frozen()
        result=reconcile(a,b,[data(0)],AFTER)
        self.assertEqual(result["statusCounts"]["PENDING"],6)
        self.assertEqual(result["scores"]["ufcash"]["eligible"],1)

    def test_all_pending_means_no_accuracy_claim(self):
        a,b=frozen()
        result=reconcile(a,b,[],AFTER)
        self.assertEqual(result["status"],"NO_SCORED_BOUTS")
        self.assertIsNone(result["scores"]["frontier"]["accuracy"])

    def test_changed_or_unknown_opponent_rejected(self):
        a,b=frozen()
        r=data(0);r["fighterB"]="Another Fighter"
        with self.assertRaisesRegex(ValueError,"unexpected bout"):
            reconcile(a,b,[r],AFTER)

    def test_duplicate_pairs_rejected(self):
        a,b=frozen()
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            reconcile(a,b,[data(0),data(0)],AFTER)

    def test_unrecognized_and_untrusted_sources_rejected(self):
        a,b=frozen()
        r=data(0);r["source_url"]="https://ufc.com.evil.example/path"
        with self.assertRaisesRegex(ValueError,"UFC-hosted"):
            reconcile(a,b,[r],AFTER)

    def test_result_cannot_exist_before_event(self):
        a,b=frozen()
        with self.assertRaisesRegex(ValueError,"before event starts"):
            reconcile(a,b,[data(0)],dt.datetime(2026,11,20,tzinfo=dt.timezone.utc))

    def test_result_source_cannot_be_backdated(self):
        a,b=frozen()
        r=data(0);r["verified_at_utc"]="2026-11-19T13:00:00Z"
        with self.assertRaisesRegex(ValueError,"precedes event"):
            reconcile(a,b,[r],AFTER)

    def test_winner_must_be_exact_fighter(self):
        a,b=frozen()
        r=data(0);r["winner"]="Other"
        with self.assertRaisesRegex(ValueError,"winning fighter"):
            reconcile(a,b,[r],AFTER)

    def test_draw_cannot_have_winner(self):
        a,b=frozen()
        r=data(0,status="DRAW",winner="A")
        with self.assertRaisesRegex(ValueError,"cannot have a winner"):
            reconcile(a,b,[r],AFTER)

    def test_name_pair_order_irrelevant_for_input_but_orientation_fixed(self):
        a,b=frozen()
        row=data(0,winner="B")
        row["fighterA"],row["fighterB"]=row["fighterB"],row["fighterA"]
        output=reconcile(a,b,[row],AFTER)
        self.assertEqual(output["bouts"][0]["resultA"],0)

    def test_wilson_does_not_inflate_perfect_micro_sample(self):
        self.assertLess(wilson_lower(7,7),.999)
        self.assertIsNone(score([])["accuracy"])


if __name__=="__main__":
    unittest.main()
