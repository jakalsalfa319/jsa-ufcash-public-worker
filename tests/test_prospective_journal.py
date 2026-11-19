import datetime as dt
import unittest
from scripts.prospective_journal import normalize,can_freeze,make_snapshot


def fixtures():
    a=[]
    b=[]
    for i in range(7):
        n="Jiri Prochazka" if i==0 else "A"+str(i)
        a.append({"red":n,"blue":"B"+str(i),"model_p_red":".64"})
        b.append({"red":n,"blue":"B"+str(i),"probRed":.61,
                  "passesFrozenConfidenceGate":False})
    a[0]["red"]="Jiří Procházka"
    return a,{"eventDate":"2026-11-21","upcomingPredictions":b}


class JournalGuards(unittest.TestCase):
    def test_accent_alias_normalized(self):
        self.assertEqual(normalize("Jiří Procházka"),normalize("Jiri Prochazka"))

    def test_real_pre_event_snapshot(self):
        a,b=fixtures()
        r=make_snapshot(a,b,"2026-11-21",
                        dt.datetime(2026,11,19,tzinfo=dt.timezone.utc),
                        {"card/upcoming.csv":"x"*64})
        self.assertEqual(r["status"],"PRE_EVENT_RESEARCH_ONLY")
        self.assertEqual(r["predictionCount"],7)
        self.assertEqual(len(r["snapshotSha256"]),64)
        self.assertTrue(all(z["outcome"] is None and z["betPlaced"] is False
                            for z in r["predictions"]))

    def test_past_event_refuses_backdating(self):
        a,b=fixtures()
        r=make_snapshot(a,b,"2026-11-21",
                        dt.datetime(2026,11,22,tzinfo=dt.timezone.utc),{})
        self.assertEqual(r["status"],"NO_PROSPECTIVE_SNAPSHOT")
        self.assertEqual(r["predictions"],[])

    def test_event_day_start_refuses_new_freeze(self):
        self.assertFalse(can_freeze("2026-11-21",
                         dt.datetime(2026,11,21,0,0,tzinfo=dt.timezone.utc)))

    def test_fighter_mismatch_refuses(self):
        a,b=fixtures()
        b["upcomingPredictions"][1]["red"]="Somebody Else"
        with self.assertRaisesRegex(ValueError,"identities differ"):
            make_snapshot(a,b,"2026-11-21",
                          dt.datetime(2026,11,19,tzinfo=dt.timezone.utc),{})

    def test_wrong_event_rejected(self):
        a,b=fixtures()
        with self.assertRaisesRegex(ValueError,"Unexpected event"):
            make_snapshot(a,b,"2026-12-05",
                          dt.datetime(2026,11,19,tzinfo=dt.timezone.utc),{})

    def test_naive_clock_rejected(self):
        with self.assertRaisesRegex(ValueError,"timezone"):
            can_freeze("2026-11-21",dt.datetime(2026,11,19))

    def test_invalid_probability_rejected(self):
        a,b=fixtures()
        a[4]["model_p_red"]="1.45"
        with self.assertRaisesRegex(ValueError,"Invalid model probability"):
            make_snapshot(a,b,"2026-11-21",
                          dt.datetime(2026,11,19,tzinfo=dt.timezone.utc),{})


if __name__ == "__main__":
    unittest.main()
