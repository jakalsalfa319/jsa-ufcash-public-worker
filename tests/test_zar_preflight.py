import copy
import datetime as dt
import json
from pathlib import Path
import unittest
from scripts.zar_preflight import assess

FIXTURE=Path(__file__).resolve().parents[1]/'research/2026-12-05-future-watchlist.json'

class PreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=json.loads(FIXTURE.read_text(encoding='utf-8'))
    def test_future_watchlist_never_places_order(self):
        x=assess(self.data,dt.date(2026,11,21))
        self.assertTrue(x['isFutureDate'])
        self.assertEqual(x['paperDecisions'],0)
        self.assertEqual(x['recordedFights'],2)
        self.assertFalse(x['modelAndOddsProvenanceAudited'])
    def test_archived_event_does_not_place_order(self):
        x=assess(self.data,dt.date(2026,12,6))
        self.assertFalse(x['isFutureDate'])
        self.assertEqual(x['stage'],'ARCHIVED_EVENT_DATE')
        self.assertEqual(x['paperDecisions'],0)
    def test_no_model_and_quote_reasons(self):
        x=assess(self.data,dt.date(2026,11,21))
        self.assertEqual(len(x['fights'][0]['missingProof']),2)
    def test_fake_official_hostname_rejected(self):
        a=copy.deepcopy(self.data)
        a['officialCardUrl']='https://www.ufc.com.evil.example/event/fake'
        with self.assertRaises(ValueError):assess(a)
    def test_duplicate_match_rejected(self):
        a=copy.deepcopy(self.data);a['fights'].append(copy.deepcopy(a['fights'][0]))
        with self.assertRaises(ValueError):assess(a)
    def test_complete_values_still_not_authenticated(self):
        a=copy.deepcopy(self.data)
        for r in a['fights']:
            r['modelPRed']=0.6;r['quote']={'sourceUrl':'https://example.com/unverified','redAmerican':-150,'blueAmerican':120}
        x=assess(a,dt.date(2026,11,21))
        self.assertEqual(x['paperDecisions'],0)
        self.assertFalse(x['modelAndOddsProvenanceAudited'])
    def test_reject_missing_fights(self):
        a=copy.deepcopy(self.data);a['fights']=[]
        with self.assertRaises(ValueError):assess(a)

if __name__=='__main__':unittest.main()
