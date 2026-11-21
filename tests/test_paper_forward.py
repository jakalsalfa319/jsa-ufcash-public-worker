import copy
import datetime as dt
import unittest
from scripts.paper_forward import freeze, settle, price, hash_payload

NOW = dt.datetime(2026, 11, 21, 21, 30, tzinfo=dt.timezone.utc)
END = dt.datetime(2026, 12, 5, 22, tzinfo=dt.timezone.utc)
SOURCE_HASH = 'a'*64


def fixture():
    return {
      'schema': 'JSA_UFCASH_FORWARD_INPUT_V1', 'eventId': 'TEST-ONLY-FUTURE-EVENT-NO-REAL-FIGHTERS',
      'eventStartUTC': '2026-12-05T22:00:00Z',
      'predictionsCapturedAtUTC': '2026-11-21T20:00:00Z',
      'predictionSourceUrl': 'https://github.com/example/test/blob/main/fixture.json',
      'predictionSourceSha256': SOURCE_HASH, 'modelId': 'TEST-ONLY-NOT-FRONTIER',
      'policy': {'demoBankroll':1000, 'stakeFraction':.01, 'maxTotalExposureFraction':.05,
                 'minExpectedRoi':.03, 'maxQuoteAgeMinutes':120},
      'fights': [{'red':'Fixture Red', 'blue':'Fixture Blue', 'modelPRed':.70,
                  'quote': {'sourceName':'TEST ONLY', 'sourceUrl':'https://example.com/fake-fixture',
                            'capturedAtUTC': '2026-11-21T21:00:00Z', 'redAmerican':-120,
                            'blueAmerican': 140}},
                {'red':'Fighter Three', 'blue':'Fighter Four', 'modelPRed':.55, 'quote':None}]
    }


class ForwardTests(unittest.TestCase):
    def test_decimal_odds(self):
        self.assertEqual(price(150),2.5)
        self.assertAlmostEqual(price(-200),1.5)
        for n in [-99, 0, 99, True, 111.5]:
            with self.assertRaises(ValueError): price(n)

    def test_fixture_only_decision_and_null_financial_claims(self):
        snap=freeze(fixture(),NOW)
        self.assertEqual(snap['paperDecisionCount'],1)
        self.assertEqual(snap['demoExposure'],10)
        self.assertFalse(snap['verifiedExecutableOdds'])
        self.assertIsNone(snap['validatedPaperRoi'])
        self.assertEqual(snap['realBetsPlaced'],0)
        self.assertEqual(snap['fights'][1]['reason'],'MISSING_PRICE_SNAPSHOT')

    def test_cannot_make_retrospective_orders(self):
        with self.assertRaisesRegex(ValueError, 'retrospective'):
            freeze(fixture(), END)

    def test_prediction_future_block(self):
        data=fixture();data['predictionsCapturedAtUTC']='2026-11-22T21:00:00Z'
        with self.assertRaises(ValueError): freeze(data, NOW)

    def test_quote_cannot_be_backdated_or_future(self):
        data=fixture();data['fights'][0]['quote']['capturedAtUTC']='2026-11-21T18:00:00Z'
        with self.assertRaises(ValueError): freeze(data,NOW)
        data=fixture();data['fights'][0]['quote']['capturedAtUTC']='2026-11-21T22:00:00Z'
        with self.assertRaises(ValueError): freeze(data,NOW)

    def test_stale_quote_is_abstention(self):
        data=fixture();data['fights'][0]['quote']['capturedAtUTC']='2026-11-21T20:10:00Z'
        data['policy']['maxQuoteAgeMinutes']=30
        snap=freeze(data,NOW)
        self.assertEqual(snap['fights'][0]['reason'],'STALE_QUOTE')
        self.assertEqual(snap['paperDecisionCount'],0)

    def test_unattributed_quote_is_abstention(self):
        data=fixture(); data['fights'][0]['quote']['sourceUrl']=''
        snap=freeze(data,NOW)
        self.assertEqual(snap['paperDecisionCount'],0)

    def test_invalid_policy_rejected(self):
        data=fixture(); data['policy']['stakeFraction']=.10
        with self.assertRaises(ValueError): freeze(data,NOW)
        data=fixture(); data['policy']['maxTotalExposureFraction']=.5
        with self.assertRaises(ValueError): freeze(data,NOW)

    def test_duplicate_bout_rejected(self):
        data=fixture(); data['fights'].append(copy.deepcopy(data['fights'][0]))
        with self.assertRaises(ValueError): freeze(data,NOW)

    def test_exposure_cap_deterministic(self):
        data=fixture()
        data['fights']=[copy.deepcopy(data['fights'][0]) for _ in range(7)]
        for i, v in enumerate(data['fights']):
            v['red']=f'R{i}'; v['blue']=f'B{i}'
        snap=freeze(data,NOW)
        self.assertEqual(snap['paperDecisionCount'],5)
        self.assertEqual(snap['demoExposure'],50)
        self.assertEqual(sum(r['reason']=='TOTAL_EXPOSURE_CAP' for r in snap['fights']),2)

    def test_no_retroactive_settlement(self):
        snap=freeze(fixture(),NOW)
        with self.assertRaises(ValueError): settle(snap,{'eventId':snap['eventId'], 'outcomes':[]},NOW)

    def test_pending_and_disputed_are_not_losses(self):
        snap=freeze(fixture(),NOW)
        out=settle(snap,{'eventId':snap['eventId'], 'outcomes':[{'red':'Fixture Red', 'blue':'Fixture Blue', 'status':'DISPUTED'}]}, END)
        self.assertEqual(out['reportedDecisiveModelFights'],0)
        self.assertIsNone(out['modelWinnerAccuracyAgainstClaimedResults'])
        self.assertIsNone(out['verifiedPaperRoi'])

    def test_scoring_assumed_result_not_promoted_to_verified(self):
        snap=freeze(fixture(),NOW)
        outcome={'eventId':snap['eventId'], 'outcomes':[{'red':'Fixture Red', 'blue':'Fixture Blue',
           'status':'COMPLETED', 'winner':'Fixture Red', 'sourceUrl':'https://ufcstats.com/fight-details/testonly',
           'observedAtUTC':'2026-12-05T23:00:00Z'}]}
        out=settle(snap,outcome, dt.datetime(2026,12,6,1,tzinfo=dt.timezone.utc))
        self.assertEqual(out['reportedDecisiveModelFights'],1)
        self.assertEqual(out['modelWinnerAccuracyAgainstClaimedResults'],1)
        self.assertGreater(out['scenarioNetAgainstClaimedResults'],0)
        self.assertIsNone(out['verifiedPaperRoi'])
        self.assertEqual(out['realBetsPlaced'],0)

    def test_hash_tampering_prevents_scoring(self):
        snap=freeze(fixture(),NOW)
        snap['fights'][0]['modelPRed']=.1
        with self.assertRaisesRegex(ValueError,'corrupted'):
            settle(snap,{'eventId':snap['eventId'],'outcomes':[]}, END)

    def test_fake_winner_disallowed(self):
        snap=freeze(fixture(),NOW)
        with self.assertRaises(ValueError): settle(snap,{'eventId':snap['eventId'], 'outcomes':[
           {'red':'Fixture Red','blue':'Fixture Blue','status':'COMPLETED', 'winner':'Someone Else',
            'sourceUrl':'https://ufcstats.com/fight-details/test','observedAtUTC':'2026-12-05T23:00:00Z'}]},END)

    def test_nonofficial_result_disallowed(self):
        snap=freeze(fixture(),NOW)
        with self.assertRaisesRegex(ValueError,'Official'):
            settle(snap,{'eventId':snap['eventId'], 'outcomes':[
           {'red':'Fixture Red','blue':'Fixture Blue','status':'COMPLETED', 'winner':'Fixture Red',
            'sourceUrl':'https://example.com/results','observedAtUTC':'2026-12-05T23:00:00Z'}]},END)

    def test_reject_duplicate_outcomes(self):
        snap=freeze(fixture(),NOW)
        claim={'red':'Fixture Red','blue':'Fixture Blue','status':'DISPUTED'}
        with self.assertRaises(ValueError): settle(snap,{'eventId':snap['eventId'],'outcomes':[claim,claim]},END)

    def test_hash_is_deterministic(self):
        self.assertEqual(hash_payload({'b':1,'a':2}), hash_payload({'a':2,'b':1}))

if __name__ == '__main__': unittest.main()