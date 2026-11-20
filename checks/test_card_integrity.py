import datetime as dt
import hashlib
import unittest
from scripts.card_integrity import (
    PAIRS,SOURCE_URLS,EVENT_DATE,paired_bouts,validate_journals,verify,canonical
)


def docs():
    classic={"schema":"JSA_EVENT_JOURNAL_V1","eventDate":EVENT_DATE,
       "status":"PRE_EVENT_RESEARCH_ONLY","generatedAtUTC":"2026-11-19T21:44:30Z",
       "predictions":[{"red":a,"blue":b,"outcome":None,"betPlaced":False}
                      for a,b in PAIRS]}
    v2={"schema":"JSA_FRONTIER_PROSPECTIVE_V2","eventDate":EVENT_DATE,
        "recordedAtUTC":"2026-11-20T14:41:29Z",
        "predictions":[{"fighterA":a,"fighterB":b,"outcome":None,"betPlaced":False}
                       for a,b in PAIRS]}
    return classic,v2


def page(missing=-1,combined=False):
    def pair_li(a,b):
        return f"<li><p>{a}</p><p>Lightweight Bout</p><p>{b}</p></li>"
    items=[pair_li(a,b) for i,(a,b) in enumerate(PAIRS) if i!=missing]
    if combined:
        items=["<li>"+" ".join(a+" vs "+b for a,b in PAIRS)+"</li>"]
    return '<html><head><title>UFC Qatar</title></head><body><h1>Nov 21 Doha</h1><ul>'+''.join(items)+'</ul></body></html>'


class CardGateTests(unittest.TestCase):
    def test_unicode_fighter_aliases(self):
        self.assertEqual(canonical("Jiří Procházka"),canonical("Jiri Prochazka"))
        self.assertEqual(canonical("Aljamain   Sterling"),canonical("Aljamain Sterling"))

    def test_same_bout_gate_passes(self):
        original,frontier=docs()
        html=page().replace("Jiri Prochazka","Jiří Procházka")
        found=paired_bouts(html)
        self.assertEqual(sum(x["officialBoutPresent"] for x in found),7)
        obj=verify(html,original,frontier,SOURCE_URLS[0],
                   dt.datetime(2026,11,20,15,0,tzinfo=dt.timezone.utc),
                   hashlib.sha256(html.encode()).hexdigest())
        self.assertTrue(obj["allSevenCurrentlyListed"])
        self.assertFalse(obj["resultsSettled"])
        self.assertFalse(obj["betsPlaced"])

    def test_one_replaced_fighter_blocks_complete(self):
        original,frontier=docs()
        x=verify(page(missing=4),original,frontier,SOURCE_URLS[0],
                 dt.datetime(2026,11,20,15,0,tzinfo=dt.timezone.utc),"a"*64)
        self.assertEqual(x["listedSameBoutCount"],6)
        self.assertEqual(x["status"],"REVIEW_CARD_CHANGE")

    def test_names_in_one_navigation_list_not_a_fight(self):
        found=paired_bouts(page(combined=True))
        self.assertEqual(sum(x["officialBoutPresent"] for x in found),0)

    def test_names_in_separate_bouts_cannot_match(self):
        html='<li>Jiri Prochazka vs Other Fighter</li><li>Navajo Stirling vs Someone Else</li>'
        self.assertFalse(paired_bouts(html)[0]["officialBoutPresent"])

    def test_changed_frozen_journal_identity_rejected(self):
        original,frontier=docs()
        frontier["predictions"][3]["fighterB"]="Other athlete"
        with self.assertRaisesRegex(ValueError,"changed"):
            validate_journals(original,frontier)

    def test_no_post_event_outcomes_allowed_in_original(self):
        original,frontier=docs()
        original["predictions"][0]["outcome"]=1
        with self.assertRaisesRegex(ValueError,"later outcomes"):
            validate_journals(original,frontier)

    def test_no_late_frozen_journal_accepted(self):
        original,frontier=docs()
        frontier["recordedAtUTC"]="2026-11-22T00:00:00Z"
        with self.assertRaisesRegex(ValueError,"genuine pre-event"):
            validate_journals(original,frontier)

    def test_observation_during_event_is_not_called_pre_event(self):
        original,frontier=docs()
        x=verify(page(),original,frontier,SOURCE_URLS[0],
                 dt.datetime(2026,11,21,18,0,tzinfo=dt.timezone.utc),"a"*64)
        self.assertTrue(x["eventStartedAtCheck"])
        self.assertFalse(x["actualBoutsCompletedVerified"])

    def test_non_official_source_rejected(self):
        original,frontier=docs()
        with self.assertRaisesRegex(ValueError,"Unrecognized official"):
            verify(page(),original,frontier,"https://random.example/card",
                   dt.datetime(2026,11,20,tzinfo=dt.timezone.utc),"a"*64)


if __name__ == "__main__":
    unittest.main()
