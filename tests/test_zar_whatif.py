import copy
import json
import unittest
from pathlib import Path
from scripts.zar_whatif import calculate, decimal_odds

FIXTURE = Path(__file__).resolve().parents[1]/'research/2026-11-21-qatar-whatif-input.json'

class RetrospectiveRandsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data=json.loads(FIXTURE.read_text(encoding='utf-8'))
    def test_american_negative(self): self.assertAlmostEqual(float(decimal_odds(-179)),1+100/179)
    def test_american_positive(self): self.assertEqual(float(decimal_odds(224)),3.24)
    def test_invalid_odds(self):
        for v in (0,99,-99,True,2.3):
            with self.subTest(v=v), self.assertRaises(ValueError): decimal_odds(v)
    def test_exact_four_selections(self):
        r=calculate(self.data)
        self.assertEqual(r['scenarioSelectionCount'],4)
        self.assertEqual([x['selection'] for x in r['selections'] if x.get('hypotheticalStakeZAR')],
                         ['Navajo Stirling','Ikram Aliskerov','Santiago Luna','Tallison Teixeira'])
    def test_known_three_win_payout(self):
        r=calculate(self.data)
        self.assertEqual(r['reportedScenarioWins'],3)
        self.assertEqual(r['reportedScenarioLosses'],0)
        self.assertEqual(r['hypotheticalNetFromReportedDecisiveZAR'],31.44)
    def test_disputed_bounds(self):
        r=calculate(self.data)
        self.assertEqual(r['unsettledScenarioSelections'],1)
        self.assertEqual(r['finalBalanceIfAllUnsettledLoseZAR'],1021.44)
        self.assertEqual(r['finalBalanceIfAllUnsettledWinZAR'],1047.94)
    def test_no_forward_claim(self):
        r=calculate(self.data)
        self.assertFalse(r['ordersFrozenBeforeFights'])
        self.assertIsNone(r['verifiedProspectiveROI'])
        self.assertEqual(r['realBetsPlaced'],0)
    def test_favorite_baseline_equal(self):
        r=calculate(self.data)
        self.assertEqual(r['reportedModelAccuracy'],{'correct':5,'n':6,'percent':83.33})
        self.assertEqual(r['reportedModelAccuracy'],r['reportedMarketFavoriteAccuracy'])
    def test_scaled_bankroll(self):
        r=calculate(self.data,'10000')
        self.assertEqual(r['stakePerSelectionZAR'],100)
        self.assertEqual(r['finalBalanceIfAllUnsettledLoseZAR'],10214.35)
        self.assertEqual(r['finalBalanceIfAllUnsettledWinZAR'],10479.35)
    def test_no_doubled_fight(self):
        d=copy.deepcopy(self.data);d['fights'].append(d['fights'][0])
        with self.assertRaisesRegex(ValueError,'Duplicate'):calculate(d)
    def test_no_winner_assigned_disputed(self):
        d=copy.deepcopy(self.data);d['fights'][-1]['reportedWinner']='Tallison Teixeira'
        with self.assertRaises(ValueError):calculate(d)
    def test_exposure_cap(self):
        d=copy.deepcopy(self.data)
        seed=d['fights'][0]
        d['fights']=[dict(seed,red=f'Synthetic Red {i}',blue=f'Synthetic Blue {i}',
                          reportedWinner=f'Synthetic Blue {i}') for i in range(6)]
        r=calculate(d,'1000','0.01','0.03')
        self.assertEqual(r['scenarioSelectionCount'],5)
        self.assertEqual(r['stakedHypotheticalZAR'],50)
    def test_negative_bankroll(self):
        with self.assertRaises(ValueError):calculate(self.data,'-1000')
    def test_empty_fights(self):
        d=copy.deepcopy(self.data);d['fights']=[]
        with self.assertRaises(ValueError):calculate(d)

if __name__=='__main__':unittest.main()
