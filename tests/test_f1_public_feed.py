import datetime as dt
import unittest
from scripts.f1_public_feed import schedule_from_response, USER_AGENT

FIXTURE={'MRData':{'RaceTable':{'Races':[
 {'season':'2026','round':'21','raceName':'Las Vegas Grand Prix','date':'2026-11-22','time':'04:00:00Z','Circuit':{'circuitName':'Las Vegas Strip Street Circuit'}},
 {'season':'2026','round':'22','raceName':'Qatar Grand Prix','date':'2026-11-29','time':'16:00:00Z','Circuit':{'circuitName':'Lusail International Circuit'}}]}}}

class F1AdapterTests(unittest.TestCase):
    def test_calendar(self):
        x=schedule_from_response(FIXTURE,dt.datetime(2026,11,21,21,0,tzinfo=dt.timezone.utc))
        self.assertEqual(x['raceCount'],2)
        self.assertEqual(x['races'][0]['status'],'UPCOMING')
        self.assertEqual(x['races'][0]['eventStartsUTC'],'2026-11-22T04:00:00Z')
        self.assertEqual(x['simulatedBets'],0)
    def test_started(self):
        x=schedule_from_response(FIXTURE,dt.datetime(2026,11,22,6,0,tzinfo=dt.timezone.utc))
        self.assertEqual(x['races'][0]['status'],'STARTED_OR_PAST')
        self.assertEqual(x['races'][1]['status'],'UPCOMING')
    def test_no_odds_mislabel(self):
        x=schedule_from_response(FIXTURE,dt.datetime(2026,11,21,21,0,tzinfo=dt.timezone.utc))
        for r in x['races']:
            self.assertFalse(r['oddsAvailableFromThisSource'])
            self.assertFalse(r['eligibleToFreezeAllInTicket'])
    def test_invalid(self):
        for value in ({},{'MRData':{}},{'MRData':{'RaceTable':{'Races':'wrong'}}}):
            with self.subTest(data=value),self.assertRaises(ValueError):
                schedule_from_response(value)
    def test_identifiable_agent(self):
        self.assertIn('UFCash',USER_AGENT)

if __name__=='__main__':unittest.main()
