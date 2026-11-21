import copy
import unittest
from datetime import datetime, timezone
from scripts.multisport_markets import rugby_union_candidate, horse_win_candidate, market_candidate
from scripts.all_in_challenge import plan_round, settle_round, INPUT

NOW = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)
SRC = 'https://example.test/synthetic/test-only-prices'

def rugby():
    return {'schema':'UFCASH_RUGBY_UNION_1X2_BOARD_V1', 'eventId':'synthetic-rugby-fixture',
            'eventStartsUTC':'2026-12-01T18:00:00Z', 'fixtureStatus':'CONFIRMED_PREMATCH',
            'homeTeam':'Synthetic Lions','awayTeam':'Synthetic Sharks',
            'market':'REGULATION_80_MIN_1X2',
            'modelProbabilities':{'home':'0.55','draw':'0.05','away':'0.40'},
            'quote':{'capturedAtUTC':'2026-12-01T09:50:00Z', 'sourceName':'TEST ONLY',
                     'sourceUrl':SRC,'priceKind':'FIXED_DECIMAL',
                     'pricesDecimal':{'home':'1.90','draw':'18.0','away':'2.40'}}}

def horse():
    return {'schema':'UFCASH_HORSE_FIXED_WIN_BOARD_V1','eventId':'synthetic-horse-race',
            'eventStartsUTC':'2026-12-01T18:20:00Z', 'raceStatus':'CONFIRMED_DECLARATIONS',
            'course':'Synthetic Racecourse','market':'FIXED_WIN',
            'runners':[{'runnerId':'r1','horseName':'Alpha Horse','modelWinProbability':'0.5','status':'DECLARED'},
                       {'runnerId':'r2','horseName':'Beta Horse','modelWinProbability':'0.3','status':'DECLARED'},
                       {'runnerId':'r3','horseName':'Gamma Horse','modelWinProbability':'0.2','status':'DECLARED'}],
            'quote':{'capturedAtUTC':'2026-12-01T09:50:00Z','sourceName':'TEST ONLY',
                     'sourceUrl':SRC,'priceKind':'FIXED_DECIMAL',
                     'pricesDecimalByRunnerId':{'r1':'2.2','r2':'4.0','r3':'6.0'}}}

def round_input(candidates):
    return {'schema': INPUT, 'roundId':'synthetic-multisport-20261201', 'strategy':'BASKET',
            'availableBankrollZAR':'2000.00', 'modelSourceUrl':'https://example.test/synthetic/frozen',
            'modelSha256':'e'*64, 'modelCapturedUTC':'2026-12-01T09:00:00Z',
            'candidates':candidates, 'minEstimatedEV':'0.03'}

class CrossSportTests(unittest.TestCase):
    def test_rugby_selects_home(self):
        c=rugby_union_candidate(rugby())
        self.assertEqual(c['selection'],'Synthetic Lions')
        self.assertEqual(c['modelPSelection'],'0.55')
        self.assertEqual(c['quote']['decimalOdds'],'1.90')
    def test_horse_selects_best_ev(self):
        c=horse_win_candidate(horse())
        self.assertEqual(c['selection'],'Beta Horse')
        self.assertEqual(c['quote']['decimalOdds'],'4.0')
    def test_complete_board_allocates_r2000(self):
        r=plan_round(round_input([rugby_union_candidate(rugby()),horse_win_candidate(horse())]),NOW)
        self.assertEqual(r['status'],'ALL_IN_FROZEN')
        self.assertEqual(r['deployedZAR'],'2000.00')
        self.assertEqual(r['uncommittedZAR'],'0.00')
        self.assertEqual([x['stakeZAR'] for x in r['selections']],['1000.00','1000.00'])
        self.assertEqual(r['realBetsPlaced'],0)
    def test_rugby_draw_is_separate_outcome(self):
        b=rugby();b['modelProbabilities']={'home':'0.25','draw':'0.50','away':'0.25'}
        c=rugby_union_candidate(b)
        self.assertEqual(c['selection'],'DRAW')
    def test_probabilities_must_sum(self):
        b=rugby();b['modelProbabilities']['home']='0.85'
        with self.assertRaisesRegex(ValueError,'sum to one'):rugby_union_candidate(b)
    def test_rugby_requires_all_three_odds(self):
        b=rugby();del b['quote']['pricesDecimal']['draw']
        with self.assertRaisesRegex(ValueError,'complete 1X2'):rugby_union_candidate(b)
    def test_rugby_extra_time_market_rejected(self):
        b=rugby();b['market']='INCLUDING_EXTRA_TIME'
        with self.assertRaisesRegex(ValueError,'Wrong market'):rugby_union_candidate(b)
    def test_horse_scratch_rejected(self):
        b=horse();b['runners'][1]['status']='SCRATCHED'
        with self.assertRaisesRegex(ValueError,'Scratched'):horse_win_candidate(b)
    def test_horse_missing_runner_price_rejected(self):
        b=horse();del b['quote']['pricesDecimalByRunnerId']['r3']
        with self.assertRaisesRegex(ValueError,'Every declared'):horse_win_candidate(b)
    def test_horse_tote_quote_rejected(self):
        b=horse();b['quote']['priceKind']='TOTE_PROJECTION'
        with self.assertRaisesRegex(ValueError,'Tote dividends'):horse_win_candidate(b)
    def test_duplicate_horse_rejected(self):
        b=horse();b['runners'][1]['runnerId']='r1'
        with self.assertRaisesRegex(ValueError,'Duplicate'):horse_win_candidate(b)
    def test_horse_probabilities_must_sum(self):
        b=horse();b['runners'][2]['modelWinProbability']='0.7'
        with self.assertRaisesRegex(ValueError,'sum to one'):horse_win_candidate(b)
    def test_quote_after_race_rejected(self):
        b=horse();b['quote']['capturedAtUTC']='2026-12-01T20:00:00Z'
        with self.assertRaisesRegex(ValueError,'after event'):horse_win_candidate(b)
    def test_no_quote_invented(self):
        b=rugby();b['quote']=None
        with self.assertRaisesRegex(ValueError,'Missing source'):rugby_union_candidate(b)
    def test_unknown_market_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unsupported'):market_candidate({'schema':'CRICKET_FAKE'})
    def test_decimal_only_acceptance(self):
        c=rugby_union_candidate(rugby());c['quote']['americanOdds']=100
        with self.assertRaisesRegex(ValueError,'exactly one'):plan_round(round_input([c]),NOW)
    def test_invalid_decimal_rejected(self):
        b=horse();b['quote']['pricesDecimalByRunnerId']['r2']='1.0'
        with self.assertRaisesRegex(ValueError,'Invalid fixed'):horse_win_candidate(b)
    def test_round_pending_locks_all_bankroll(self):
        rc=plan_round(round_input([rugby_union_candidate(rugby()),horse_win_candidate(horse())]),NOW)
        settlement=settle_round(rc,[],datetime(2026,12,2,tzinfo=timezone.utc))
        self.assertEqual(settlement['status'],'OPEN_DISPUTED_OR_PENDING')
        self.assertIsNone(settlement['nextAvailableBalanceZAR'])
    def test_round_all_losses_go_bankrupt(self):
        rc=plan_round(round_input([rugby_union_candidate(rugby()),horse_win_candidate(horse())]),NOW)
        outcomes=[{'eventId':b['eventId'],'status':'LOSS','sourceUrl':SRC,
                   'observedAtUTC':'2026-12-01T20:00:00Z'} for b in rc['selections']]
        s=settle_round(rc,outcomes,datetime(2026,12,2,tzinfo=timezone.utc))
        self.assertEqual(s['nextAvailableBalanceZAR'],'0.00')
    def test_invalid_bool_decimal_rejected(self):
        b=horse();b['quote']['pricesDecimalByRunnerId']['r2']=True
        with self.assertRaises(ValueError):horse_win_candidate(b)

if __name__=='__main__':unittest.main()
