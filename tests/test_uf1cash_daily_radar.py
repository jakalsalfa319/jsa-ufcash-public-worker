"""Daily five-sport watch safeguards. All examples are schedule-only."""
import copy
import datetime as dt
import json
import unittest
from pathlib import Path
from scripts.uf1cash_daily_radar import overview,SPORTS,TZ_SAST

BASE=Path(__file__).resolve().parents[1]
NOW=dt.datetime(2026,11,22,10,0,tzinfo=TZ_SAST)
def fixtures():
    return (
        json.loads((BASE/"public/uf1cash-goal.json").read_text()),
        json.loads((BASE/"records/uf1cash/challenge-policy-v3.json").read_text()),
        json.loads((BASE/"research/uf1cash-five-sport-fixture-watch.json").read_text())
    )

class RadarTests(unittest.TestCase):
    def test_watch_five_sports_and_no_bets(self):
        r=overview(*fixtures(),at=NOW)
        self.assertEqual(tuple(r["sports"]),SPORTS)
        self.assertEqual(r["workingAvailableVirtualZAR"],"3071.74")
        self.assertEqual(r["validatedPreEventSelections"],0)
        self.assertEqual(r["realBetsPlaced"],0)
        self.assertTrue(r["noMarketQuoteOrPredictiveModelDataInWatchlist"])
        self.assertGreater(r["scheduledEventsListed"],5)
    def test_scrub_old_fixture_dates(self):
        a,b,c=fixtures()
        r=overview(a,b,c,at=dt.datetime(2026,12,15,12,tzinfo=TZ_SAST))
        self.assertEqual(r["scheduledEventsListed"],0)
    def test_no_fake_bet_from_calendar_even_if_f1_present(self):
        a,b,c=fixtures()
        f1={"schema":"UFCASH_F1_SOURCE_FEED_V1",
            "races":[{"status":"UPCOMING"},{"status":"STARTED_OR_PAST"}]}
        r=overview(a,b,c,at=NOW,f1=f1)
        self.assertEqual(r["sports"]["F1"]["jolpicaUpcomingRaceCount"],1)
        self.assertEqual(r["validatedPreEventSelections"],0)
    def test_duplicate_fixture_refused(self):
        a,b,c=fixtures();c=copy.deepcopy(c)
        c["fixtures"].append(c["fixtures"][0])
        with self.assertRaisesRegex(ValueError,"Duplicate"):overview(a,b,c,at=NOW)
    def test_unknown_sport_refused(self):
        a,b,c=fixtures();c=copy.deepcopy(c)
        c["fixtures"][0]["sport"]="SOCCER"
        with self.assertRaisesRegex(ValueError,"unapproved"):overview(a,b,c,at=NOW)
    def test_no_wager_policy_change(self):
        a,b,c=fixtures();a=copy.deepcopy(a);a["allInAllocationPercent"]=50
        with self.assertRaisesRegex(ValueError,"milestone"):overview(a,b,c,at=NOW)
    def test_results_do_not_populate_paper_bets(self):
        a,b,c=fixtures();c=copy.deepcopy(c)
        c["fixtures"][0]["claimedWinner"]="Synthetic Fighter"
        c["fixtures"][0]["price"]="+500"
        r=overview(a,b,c,at=NOW)
        self.assertFalse(r["sports"]["UFC"]["events"][0]["paperBetEligible"])
    def test_licence_source_provenance(self):
        a,b,c=fixtures()
        self.assertTrue(all(x["sourceUrl"].startswith("https://") for x in c["fixtures"]))
        r=overview(a,b,c,at=NOW)
        self.assertEqual(r["sports"]["CRICKET"]["modelAndQuoteEligibleCount"],0)

if __name__=="__main__":unittest.main()
