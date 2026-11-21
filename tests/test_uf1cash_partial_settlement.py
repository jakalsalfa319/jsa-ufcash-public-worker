import copy
import unittest
from datetime import datetime,timezone
from scripts.all_in_challenge import INPUT, plan_round
from scripts.uf1cash_partial_settlement import partial_settlement
NOW=datetime(2026,11,30,12,0,tzinfo=timezone.utc)
AFTER=datetime(2026,12,1,12,0,tzinfo=timezone.utc)

def fixture():
    return {'schema':INPUT,'roundId':'test-future-all-in','strategy':'BASKET',
        'availableBankrollZAR':'2000.00','minEstimatedEV':'0.03',
        'modelSourceUrl':'https://example.org/model/frozen.json','modelSha256':'f'*64,
        'modelCapturedUTC':'2026-11-30T11:00:00Z',
        'candidates':[{'eventId':f'bout-{n}','sport':'UFC','market':'moneyline','selection':f'A{n}',
             'eventStartsUTC':'2026-11-30T16:00:00Z','modelPSelection':'.65',
             'quote':{'americanOdds':100,'sourceUrl':'https://example.org/odds/fake',
                      'sourceName':'synthetic','capturedAtUTC':'2026-11-30T11:45:00Z'}}
             for n in range(4)]}

def outcome(event,status):
    return {'eventId':event,'status':status,
        'sourceUrl':'https://example.org/results/test','observedAtUTC':'2026-11-30T18:00:00Z'}

class PartialVirtualSettlementTests(unittest.TestCase):
    def test_three_paid_one_disputed_stake_not_reused(self):
        snap=plan_round(fixture(),NOW)
        r=partial_settlement(snap,[outcome(f'bout-{i}','WIN') for i in range(3)]+[
              {'eventId':'bout-3','status':'DISPUTED'}],AFTER)
        self.assertEqual(r['currentlyAvailableFromPaidReturnsZAR'],'3000.00')
        self.assertEqual(r['lockedUnresolvedOriginalStakesZAR'],'500.00')
        self.assertEqual(r['usableZARForNextAllInRound'],'3000.00')
        self.assertFalse(r['completed'])
        self.assertIsNone(r['verifiedProspectiveProfitZAR'])
    def test_all_loss_bankruptcy(self):
        snap=plan_round(fixture(),NOW)
        r=partial_settlement(snap,[outcome(f'bout-{i}','LOSS') for i in range(4)],AFTER)
        self.assertEqual(r['currentlyAvailableFromPaidReturnsZAR'],'0.00')
        self.assertFalse(r['canReusePaidReturnsForNewFullyStakedVirtualRound'])
    def test_unsettled_exposure_not_credited(self):
        snap=plan_round(fixture(),NOW)
        r=partial_settlement(snap,[],AFTER)
        self.assertEqual(r['lockedUnresolvedOriginalStakesZAR'],'2000.00')
        self.assertEqual(r['currentlyAvailableFromPaidReturnsZAR'],'0.00')
    def test_void_returns_stake_only(self):
        snap=plan_round(fixture(),NOW)
        r=partial_settlement(snap,[outcome(f'bout-{i}','VOID') for i in range(4)],AFTER)
        self.assertEqual(r['currentlyAvailableFromPaidReturnsZAR'],'2000.00')
        self.assertTrue(r['completed'])
    def test_tampered_receipt_rejected(self):
        snap=plan_round(fixture(),NOW)
        snap=copy.deepcopy(snap);snap['selections'][0]['stakeZAR']='999.00'
        with self.assertRaises(ValueError):partial_settlement(snap,[],AFTER)
    def test_results_cannot_predate_start(self):
        snap=plan_round(fixture(),NOW)
        r=outcome('bout-0','WIN');r['observedAtUTC']='2026-11-30T14:00:00Z'
        with self.assertRaises(ValueError):partial_settlement(snap,[r],AFTER)
    def test_strict_no_real_bets(self):
        snap=plan_round(fixture(),NOW)
        snap=copy.deepcopy(snap);snap['realBetsPlaced']=1
        with self.assertRaises(ValueError):partial_settlement(snap,[],AFTER)

if __name__=='__main__':unittest.main()
