import datetime as dt
import unittest
from scripts.prospective_journal import make_snapshot
from scripts.settle_prospective import reconcile, metrics


def setup():
    fights=[{"red":"A"+str(i),"blue":"B"+str(i),"model_p_red":".62"} for i in range(7)]
    lab={"eventDate":"2026-11-21","upcomingPredictions":[
        {"red":"A"+str(i),"blue":"B"+str(i),"probRed":.61,
         "passesFrozenConfidenceGate":False} for i in range(7)]}
    snapshot=make_snapshot(fights,lab,"2026-11-21",
       dt.datetime(2026,11,19,tzinfo=dt.timezone.utc),{})
    outcomes=[{"red":"A"+str(i),"blue":"B"+str(i),"outcome_red":"1",
       "source_url":"https://example.com/official-fight-report",
       "verified_at_utc":"2026-11-22T00:00:00Z"} for i in range(7)]
    return snapshot,outcomes


class SettlementGuards(unittest.TestCase):
    def test_seven_decisive_results_scored_but_not_profit(self):
        snapshot,outcomes=setup()
        r=reconcile(snapshot,outcomes,dt.datetime(2026,11,22,tzinfo=dt.timezone.utc))
        self.assertEqual(r["ufcash"]["correct"],7)
        self.assertEqual(r["oddsFree"]["count"],7)
        self.assertTrue(r["noROIClaim"])
        self.assertTrue(r["noWagersPlaced"])

    def test_no_early_settlement(self):
        snapshot,outcomes=setup()
        with self.assertRaisesRegex(ValueError,"before the event"):
            reconcile(snapshot,outcomes,dt.datetime(2026,11,19,tzinfo=dt.timezone.utc))

    def test_bout_mismatch_fails(self):
        snapshot,outcomes=setup()
        outcomes[0]["red"]="Elsewhere"
        with self.assertRaisesRegex(ValueError,"Expected bout"):
            reconcile(snapshot,outcomes,dt.datetime(2026,11,22,tzinfo=dt.timezone.utc))

    def test_draw_and_nc_not_win_or_loss(self):
        snapshot,outcomes=setup()
        outcomes[0]["outcome_red"]="DRAW"
        outcomes[1]["outcome_red"]="NC"
        r=reconcile(snapshot,outcomes,dt.datetime(2026,11,22,tzinfo=dt.timezone.utc))
        self.assertEqual(r["ufcash"]["count"],5)
        self.assertEqual(r["drawOrNC"],2)

    def test_duplicate_outcome_rejected(self):
        snapshot,outcomes=setup()
        outcomes[2]=dict(outcomes[1])
        with self.assertRaisesRegex(ValueError,"duplicate outcome"):
            reconcile(snapshot,outcomes,dt.datetime(2026,11,22,tzinfo=dt.timezone.utc))

    def test_no_evidence_source_rejected(self):
        snapshot,outcomes=setup()
        outcomes[1]["source_url"]="not-a-source"
        with self.assertRaisesRegex(ValueError,"HTTPS"):
            reconcile(snapshot,outcomes,dt.datetime(2026,11,22,tzinfo=dt.timezone.utc))

    def test_no_empty_accuracy_fabrication(self):
        self.assertIsNone(metrics([])["accuracy"])


if __name__=="__main__":
    unittest.main()
