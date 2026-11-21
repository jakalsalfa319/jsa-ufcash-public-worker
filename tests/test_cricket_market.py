"""Synthetic cricket market and Cricsheet no-lookahead checks."""
import unittest
from datetime import datetime,timezone
from scripts.multisport_markets import market_candidate,cricket_t20_candidate
from scripts.cricsheet_history import history_row
from scripts.uf1cash_challenge import prepare
from scripts.all_in_challenge import cents
from pathlib import Path
import json

NOW=datetime(2026,12,1,10,0,tzinfo=timezone.utc)

def board():
    return {"schema":"UF1CASH_CRICKET_T20_MATCH_WINNER_BOARD_V1",
        "eventId":"test-cricket","eventStartsUTC":"2026-12-01T18:00:00Z",
        "matchFormat":"T20","matchStatus":"CONFIRMED_PREMATCH",
        "teamA":"Synthetic Lions","teamB":"Synthetic Kings",
        "market":"T20_MATCH_WINNER_INCLUDING_SUPER_OVER",
        "modelProbabilities":{"team_a":"0.60","team_b":"0.40"},
        "quote":{"capturedAtUTC":"2026-12-01T09:45:00Z","sourceName":"synthetic",
                 "sourceUrl":"https://example.test/cricket/prices","priceKind":"FIXED_DECIMAL",
                 "pricesDecimal":{"team_a":"1.85","team_b":"2.30"}}}

def match():
    return {"info":{"match_type":"T20","dates":["2025-02-03"],"teams":["Synthetic Lions","Synthetic Kings"],"outcome":{"winner":"Synthetic Lions"}}}

def ready():
    root=Path(__file__).resolve().parents[1]
    return (json.loads((root/"public/uf1cash-status.json").read_text()),
            json.loads((root/"records/uf1cash/challenge-policy-v3.json").read_text()))

def paper(*candidates):
    return {"schema":"UFCASH_ALLIN_INPUT_V1","roundId":"test-cricket-round",
        "strategy":"BASKET","availableBankrollZAR":"3071.74",
        "modelSourceUrl":"https://example.test/cricket/frozen-model","modelSha256":"f"*64,
        "modelCapturedUTC":"2026-12-01T09:30:00Z","minEstimatedEV":"0.03",
        "candidates":list(candidates)}

class CricketTests(unittest.TestCase):
    def test_cricket_selection(self):
        c=cricket_t20_candidate(board())
        self.assertEqual((c["selection"],c["sport"]),("Synthetic Lions","CRICKET"))
        self.assertEqual(c["quote"]["decimalOdds"],"1.85")
    def test_cricket_dispatch(self):
        self.assertEqual(market_candidate(board())["sport"],"CRICKET")
    def test_cricket_can_select_other_side(self):
        x=board();x["modelProbabilities"]={"team_a":"0.35","team_b":"0.65"}
        self.assertEqual(cricket_t20_candidate(x)["selection"],"Synthetic Kings")
    def test_cricket_probability_sum(self):
        x=board();x["modelProbabilities"]["team_a"]="0.8"
        with self.assertRaisesRegex(ValueError,"sum to one"):cricket_t20_candidate(x)
    def test_no_one_sided_odds(self):
        x=board();del x["quote"]["pricesDecimal"]["team_b"]
        with self.assertRaisesRegex(ValueError,"Both teams require fixed"):cricket_t20_candidate(x)
    def test_reject_inplay(self):
        x=board();x["matchStatus"]="IN_PLAY"
        with self.assertRaisesRegex(ValueError,"not confirmed"):cricket_t20_candidate(x)
    def test_reject_test_match(self):
        x=board();x["matchFormat"]="TEST"
        with self.assertRaisesRegex(ValueError,"Only T20"):cricket_t20_candidate(x)
    def test_reject_wrong_settlement(self):
        x=board();x["market"]="REGULATION_WINNER"
        with self.assertRaisesRegex(ValueError,"Wrong market"):cricket_t20_candidate(x)
    def test_reject_tote_or_indicative(self):
        x=board();x["quote"]["priceKind"]="INDICATIVE"
        with self.assertRaisesRegex(ValueError,"fixed-odds"):cricket_t20_candidate(x)
    def test_reject_late_quote(self):
        x=board();x["quote"]["capturedAtUTC"]="2026-12-01T18:20:00Z"
        with self.assertRaisesRegex(ValueError,"after event"):cricket_t20_candidate(x)
    def test_single_sport_full_wallet(self):
        w,p=ready();r=prepare(w,p,paper(cricket_t20_candidate(board())),NOW)["receipt"]
        self.assertEqual((r["deployedZAR"],r["uncommittedZAR"]),("3071.74","0.00"))
    def test_three_way_cricket_rugby_horse_bundle(self):
        from scripts.multisport_markets import rugby_union_candidate,horse_win_candidate
        rub={"schema":"UFCASH_RUGBY_UNION_1X2_BOARD_V1","eventId":"test-rugby",
            "eventStartsUTC":"2026-12-01T18:00:00Z","fixtureStatus":"CONFIRMED_PREMATCH",
            "homeTeam":"Rugby A","awayTeam":"Rugby B","market":"REGULATION_80_MIN_1X2",
            "modelProbabilities":{"home":"0.55","draw":"0.05","away":"0.40"},
            "quote":{"capturedAtUTC":"2026-12-01T09:45:00Z","sourceName":"synthetic",
              "sourceUrl":"https://example.test/rugby/quote","priceKind":"FIXED_DECIMAL",
              "pricesDecimal":{"home":"1.9","draw":"18","away":"2.4"}}}
        horse={"schema":"UFCASH_HORSE_FIXED_WIN_BOARD_V1","eventId":"test-horse",
            "eventStartsUTC":"2026-12-01T18:10:00Z","raceStatus":"CONFIRMED_DECLARATIONS",
            "course":"Synthetic","market":"FIXED_WIN",
            "runners":[{"runnerId":"a","horseName":"Horse A","modelWinProbability":"0.55","status":"DECLARED"},
                       {"runnerId":"b","horseName":"Horse B","modelWinProbability":"0.45","status":"DECLARED"}],
            "quote":{"capturedAtUTC":"2026-12-01T09:45:00Z","sourceName":"synthetic",
               "sourceUrl":"https://example.test/horse/quote","priceKind":"FIXED_DECIMAL",
               "pricesDecimalByRunnerId":{"a":"2.1","b":"2.1"}}}
        w,p=ready()
        r=prepare(w,p,paper(rugby_union_candidate(rub),horse_win_candidate(horse),cricket_t20_candidate(board())),NOW)["receipt"]
        self.assertEqual(len(r["selections"]),3)
        self.assertEqual(sum(cents(x["stakeZAR"]) for x in r["selections"]),307174)
        self.assertEqual(r["uncommittedZAR"],"0.00")
    def test_history_attribution_and_no_odds(self):
        r=history_row(match(),"2026-11-22")
        self.assertEqual(r["historicalWinner"],"Synthetic Lions")
        self.assertEqual(r["requiredAttribution"],"Cricsheet.org (ODC-BY 1.0)")
        self.assertFalse(r["qualifyingForwardBet"])
        self.assertIsNone(r["odds"])
    def test_training_cutoff_no_leak(self):
        with self.assertRaisesRegex(ValueError,"LOOKAHEAD_BLOCKED"):history_row(match(),"2025-02-03")
    def test_bad_winner(self):
        a=match();a["info"]["outcome"]["winner"]="Third team"
        with self.assertRaisesRegex(ValueError,"Winner not"):history_row(a,"2026-11-22")
    def test_no_result_not_win(self):
        a=match();a["info"]["outcome"]={"result":"no result"}
        r=history_row(a,"2026-11-22")
        self.assertEqual(r["resultType"],"NON_DECISIVE")
        self.assertIsNone(r["historicalWinner"])

if __name__=="__main__":unittest.main()
