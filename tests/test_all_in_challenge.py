import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from scripts.all_in_challenge import (INPUT, plan_round, settle_round, historical_qatar_allin,
                                      weights_split, cents, odds_to_decimal, fingerprint, zar)

BASE=Path(__file__).resolve().parents[1]
NOW=datetime(2026,11,30,12,0,tzinfo=timezone.utc)

def candidate(event='match1', selection='Home', sport='football', quote_at='2026-11-30T11:45:00Z', american=120, p='0.50'):
    return {'eventId':event,'sport':sport,'market':'moneyline','selection':selection,
            'eventStartsUTC':'2026-11-30T16:00:00Z','modelPSelection':p,
            'quote':{'americanOdds':american,'sourceUrl':'https://example.org/odds/fixture',
                     'sourceName':'test-only price fixture','capturedAtUTC':quote_at}}

def example(strategy='BASKET',candidates=None):
    return {'schema':INPUT,'roundId':'fake-2026-11-30','strategy':strategy,
            'availableBankrollZAR':'2000.00', 'minEstimatedEV':'0.03',
            'modelSourceUrl':'https://example.org/frozen/model.json',
            'modelSha256':'f'*64,'modelCapturedUTC':'2026-11-30T11:30:00Z',
            'candidates':candidates or [candidate(),candidate('match2','Driver X','F1',american=-150,p='0.70')]}

class AllInVirtualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((BASE/'research/2026-11-21-qatar-reference-input.json').read_text())

    def test_basket_exact_all_in(self):
        x=plan_round(example(),NOW)
        self.assertEqual(x['deployedZAR'],'2000.00')
        self.assertEqual(x['uncommittedZAR'],'0.00')
        self.assertEqual(sum(cents(b['stakeZAR']) for b in x['selections']),200000)
        self.assertEqual(x['realBetsPlaced'],0)
        self.assertFalse(x['isVerifiedExecutableQuote'])

    def test_single_exact_all_in(self):
        x=plan_round(example('SINGLE'),NOW)
        self.assertEqual(len(x['selections']),1)
        self.assertEqual(x['selections'][0]['stakeZAR'],'2000.00')
        self.assertEqual(x['selections'][0]['selection'],'Driver X') # higher modeled EV than Home

    def test_basket_odd_pennies_all_used(self):
        a=weights_split(200003,[1,1,1])
        self.assertEqual(a,[66668,66668,66667])
        self.assertEqual(sum(a),200003)

    def test_negative_or_zero_balance(self):
        for x in ('0','-0.01','-2000'):
            y=example();y['availableBankrollZAR']=x
            with self.subTest(balance=x),self.assertRaises(ValueError):plan_round(y,NOW)

    def test_balance_fractional_cent_rejected(self):
        x=example();x['availableBankrollZAR']='2000.001'
        with self.assertRaises(ValueError):plan_round(x,NOW)

    def test_no_qualifying_bet_keeps_all(self):
        x=plan_round(example(candidates=[candidate(p='0.1')]),NOW)
        self.assertEqual(x['status'],'ABSTAIN_NO_QUALIFIED_MARKET')
        self.assertEqual(x['deployedZAR'],'0.00')
        self.assertEqual(x['uncommittedZAR'],'2000.00')

    def test_missing_quote_abstains(self):
        f=candidate();f['quote']=None
        x=plan_round(example(candidates=[f]),NOW)
        self.assertEqual(x['skipped'][0]['reason'],'NO_QUOTE')

    def test_stale_quote_abstains(self):
        data=example(candidates=[candidate(quote_at='2026-11-30T08:00:00Z')])
        data['modelCapturedUTC']='2026-11-30T07:30:00Z'
        x=plan_round(data,NOW)
        self.assertEqual(x['skipped'][0]['reason'],'STALE_QUOTE')

    def test_started_event_no_fabricated_ticket(self):
        f=candidate();f['eventStartsUTC']='2026-11-30T10:00:00Z'
        x=plan_round(example(candidates=[f]),NOW)
        self.assertEqual(x['status'],'ABSTAIN_NO_QUALIFIED_MARKET')

    def test_quote_from_future_rejected(self):
        with self.assertRaisesRegex(ValueError,'chronology'):
            plan_round(example(candidates=[candidate(quote_at='2026-11-30T13:00:00Z')]),NOW)

    def test_duplicate_event_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):
            plan_round(example(candidates=[candidate(),candidate()]),NOW)

    def test_round_fingerprint_tampering_rejected(self):
        r=plan_round(example(),NOW)
        r['selections'][0]['stakeZAR']='1.00'
        with self.assertRaisesRegex(ValueError,'tampered'):
            settle_round(r,[],datetime(2026,12,1,tzinfo=timezone.utc))

    def test_pending_locks_bankroll(self):
        r=plan_round(example(),NOW)
        x=settle_round(r,[],datetime(2026,12,1,tzinfo=timezone.utc))
        self.assertEqual(x['status'],'OPEN_DISPUTED_OR_PENDING')
        self.assertEqual(x['lockedPendingZAR'],'2000.00')
        self.assertIsNone(x['nextAvailableBalanceZAR'])

    def test_result_before_event_rejected(self):
        r=plan_round(example('SINGLE'),NOW)
        outcomes=[{'eventId':r['selections'][0]['eventId'],'status':'WIN',
           'sourceUrl':'https://example.org/results/1','observedAtUTC':'2026-11-30T15:00:00Z'}]
        with self.assertRaisesRegex(ValueError,'outside permissible'):
            settle_round(r,outcomes,datetime(2026,12,1,tzinfo=timezone.utc))

    def test_full_loss_bankrupt(self):
        r=plan_round(example('SINGLE'),NOW)
        outcomes=[{'eventId':r['selections'][0]['eventId'],'status':'LOSS',
           'sourceUrl':'https://example.org/results/1','observedAtUTC':'2026-11-30T17:00:00Z'}]
        x=settle_round(r,outcomes,datetime(2026,12,1,tzinfo=timezone.utc))
        self.assertEqual(x['nextAvailableBalanceZAR'],'0.00')
        self.assertEqual(x['provisionalNetZAR'],'-2000.00')
        self.assertIsNone(x['verifiedProspectiveProfitZAR'])

    def test_full_win_grows_bankroll(self):
        r=plan_round(example('SINGLE'),NOW)
        outcomes=[{'eventId':r['selections'][0]['eventId'],'status':'WIN',
           'sourceUrl':'https://example.org/results/1','observedAtUTC':'2026-11-30T17:00:00Z'}]
        x=settle_round(r,outcomes,datetime(2026,12,1,tzinfo=timezone.utc))
        self.assertEqual(x['nextAvailableBalanceZAR'],'3333.33')

    def test_void_returns_full_capital(self):
        r=plan_round(example('SINGLE'),NOW)
        outcomes=[{'eventId':r['selections'][0]['eventId'],'status':'VOID',
          'sourceUrl':'https://example.org/results/1','observedAtUTC':'2026-11-30T17:00:00Z'}]
        x=settle_round(r,outcomes,datetime(2026,12,1,tzinfo=timezone.utc))
        self.assertEqual(x['nextAvailableBalanceZAR'],'2000.00')

    def test_unresolved_dispute_does_not_count_as_win(self):
        r=plan_round(example('SINGLE'),NOW)
        x=settle_round(r,[{'eventId':r['selections'][0]['eventId'],'status':'DISPUTED'}],datetime(2026,12,1,tzinfo=timezone.utc))
        self.assertIsNone(x['nextAvailableBalanceZAR'])

    def test_historical_single_allin_range(self):
        x=historical_qatar_allin(self.fixture,'2000','SINGLE')
        self.assertEqual(x['selectionCount'],1)
        self.assertEqual(x['selections'][0]['selection'],'Tallison Teixeira')
        self.assertEqual(x['uncommittedZAR'],'0.00')
        self.assertEqual(x['finalBankrollIfAllUnresolvedLoseZAR'],'0.00')
        self.assertEqual(x['finalBankrollIfAllUnresolvedWinZAR'],'5300.00')
        self.assertIsNone(x['prospectiveROI'])

    def test_historical_basket_allin_range(self):
        x=historical_qatar_allin(self.fixture,'2000','BASKET')
        self.assertEqual(x['selectionCount'],4)
        self.assertEqual(x['exposureZAR'],'2000.00')
        self.assertEqual(x['uncommittedZAR'],'0.00')
        self.assertEqual([a['virtualStakeZAR'] for a in x['selections']], ['500.00']*4)
        self.assertEqual(x['finalBankrollIfAllUnresolvedLoseZAR'],'3071.74')
        self.assertEqual(x['finalBankrollIfAllUnresolvedWinZAR'],'4396.74')

    def test_missing_result_not_marked_win(self):
        x=historical_qatar_allin(self.fixture,'2000','BASKET')
        self.assertEqual(sum(i['scenarioResult']=='WIN' for i in x['selections']),3)
        self.assertEqual(sum(i['scenarioResult'].startswith('UNRESOLVED') for i in x['selections']),1)

    def test_no_duplicate_historical_pairs(self):
        y=copy.deepcopy(self.fixture);y['fights'].append(y['fights'][0])
        with self.assertRaises(ValueError):historical_qatar_allin(y)

    def test_odds_parsing(self):
        self.assertEqual(odds_to_decimal(224),__import__('decimal').Decimal('3.24'))
        self.assertAlmostEqual(float(odds_to_decimal(-179)),1.558659217877095)
        for invalid in (0,99,-1,True,0.5):
            with self.subTest(odds=invalid), self.assertRaises(ValueError): odds_to_decimal(invalid)

    def test_growth_math_honest(self):
        # Fair 50/50 bets at 2.0 decimal; 10 wins imply 0.09765625% survival.
        self.assertEqual(2000*2**10,2048000)
        self.assertAlmostEqual(.5**10*100,.09765625)

if __name__=='__main__':unittest.main()
