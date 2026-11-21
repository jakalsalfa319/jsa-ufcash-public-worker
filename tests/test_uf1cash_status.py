"""UF1Cash bookkeeping invariants. No external APIs or real bets."""
import copy
import json
import unittest
from pathlib import Path
from scripts.uf1cash_status import summary, active_summary

ROOT=Path(__file__).resolve().parents[1]
FILES=['public/ufcash-r2000-allin-genesis.json','research/2026-11-21-qatar-reference-input.json','research/uf1cash-qatar-2026-11-21-evidence-v1.json']
def fixture(): return [json.loads((ROOT/f).read_text(encoding='utf-8')) for f in FILES]

class Uf1CashStatusTests(unittest.TestCase):
    def test_baseline_balances_separate(self):
        x=summary(*fixture())
        self.assertEqual(x['prospectiveWallet']['balanceAvailableZAR'],'2000.00')
        self.assertEqual(x['prospectiveWallet']['validPreEventPaperSelections'],0)
        self.assertFalse(x['pastCardRecord']['liveChallengeBankrollAffected'])
    def test_evidence_dispute_preserved(self):
        x=summary(*fixture())
        s=x['pastCardRecord']
        self.assertEqual(s['reportedFightModelWinnerScore']['eligible'],6)
        self.assertEqual(s['reportedFightModelWinnerScore']['correct'],5)
        self.assertEqual(sum(z['scenarioResult'].startswith('UNRESOLVED') for z in s['basket']['selections']),1)
        self.assertIn('Gaziev',s['disputedBout'])
    def test_historical_full_exposure_and_range(self):
        x=summary(*fixture())['pastCardRecord']
        self.assertEqual(x['basket']['totalSimulatedStakesZAR'],'2000.00')
        self.assertEqual(x['basket']['ifDisputedLosesFinalZAR'],'3071.74')
        self.assertEqual(x['basket']['ifDisputedWinsFinalZAR'],'4396.74')
        self.assertEqual(x['basket']['ifDisputedLosesNetZAR'],'1071.74')
        self.assertEqual(x['basket']['ifDisputedWinsNetZAR'],'2396.74')
        self.assertEqual(x['singleAlternative']['ifDisputedLosesFinalZAR'],'0.00')
        self.assertEqual(x['singleAlternative']['ifDisputedWinsFinalZAR'],'5300.00')
    def test_scenarios_not_double_counted(self):
        x=summary(*fixture())['pastCardRecord']
        self.assertTrue(x['separateMutuallyExclusiveHypotheses'])
        self.assertEqual(x['recordedPaperBetsBeforeEvent'],0)
        self.assertEqual(x['realBets'],0)
    def test_stake_vs_work_allocation(self):
        x=summary(*fixture())
        self.assertEqual(x['developmentFocusPercent'],{'UFC':75,'F1':25})
        self.assertTrue(x['developmentFocusIsNotStakeSplit'])
        self.assertEqual(x['eligibleForwardSports'],['UFC','F1'])
        self.assertTrue(all(v.startswith('ON_HOLD') for v in x['researchBench'].values()))
    def test_changed_fighter_or_winner_rejected(self):
        a,b,c=fixture(); c=copy.deepcopy(c)
        c['outcomes'][0]['reportedWinner']='Jiri Prochazka'
        with self.assertRaisesRegex(ValueError,'disagree'):summary(a,b,c)
    def test_disputed_auto_win_rejected(self):
        a,b,c=fixture(); c=copy.deepcopy(c)
        c['outcomes'][-1]['reportedWinner']='Tallison Teixeira'
        with self.assertRaisesRegex(ValueError,'disagree'):summary(a,b,c)
    def test_wrong_genesis_rejected(self):
        a,b,c=fixture(); a=copy.deepcopy(a)
        a['availableVirtualZAR']='4396.74'
        with self.assertRaisesRegex(ValueError,'Wallet has changed'):summary(a,b,c)
    def test_generated_current_status_bytewise_reproducible(self):
        a,b,c=fixture()
        expected=json.loads((ROOT/'records/uf1cash/status-snapshot-v1.json').read_text(encoding='utf-8'))
        self.assertEqual(summary(a,b,c),expected)
    def test_historical_event_archive_matches_recomputed_book(self):
        a,b,c=fixture()
        archive=json.loads((ROOT/'records/uf1cash/2026-11-21-qatar-whatif-v1.json').read_text(encoding='utf-8'))
        self.assertEqual(archive['schema'],'UF1CASH_HISTORICAL_EVENT_RECORD_V1')
        self.assertEqual(archive['virtualZAR'],summary(a,b,c)['pastCardRecord'])
        self.assertEqual(archive['classification'],'RETROSPECTIVE_ONLY_NOT_RECORDED_BEFORE_EVENT')
    def test_active_scope_revision_only_in_v2_wallet(self):
        from scripts.uf1cash_status import active_summary
        a,b,c=fixture()
        auth=json.loads((ROOT/"records/uf1cash/wallet-rollover-authorization-v2.json").read_text())
        v2=active_summary(a,b,c,auth)
        self.assertEqual(v2["developmentFocusPercent"],
            {"UFC":50,"F1":12.5,"RUGBY_UNION":12.5,"HORSE_RACING":12.5,"CRICKET":12.5})
        self.assertEqual(v2["eligibleForwardSports"],
            ["UFC","F1","RUGBY_UNION","HORSE_RACING","CRICKET"])
        self.assertNotIn("horse_racing",v2["researchBench"])
        self.assertEqual(v2["currentBalanceZAR"],"3071.74")

    def test_active_wallet_rollforward_is_3071(self):
        a,b,c=fixture()
        authorization=json.loads((ROOT/'records/uf1cash/wallet-rollover-authorization-v2.json').read_text(encoding='utf-8'))
        current=active_summary(a,b,c,authorization)
        self.assertEqual(current['currentBalanceZAR'],'3071.74')
        self.assertEqual(current['prospectiveWallet']['committedZAR'],'500.00')
        self.assertEqual(current['prospectiveWallet']['validPreEventPaperSelections'],0)
        self.assertTrue(current['pastCardRecord']['liveChallengeBankrollAffected'])
        self.assertEqual(current,json.loads((ROOT/'public/uf1cash-status.json').read_text(encoding='utf-8')))
    def test_active_rollforward_cannot_credit_dispute(self):
        a,b,c=fixture()
        authorization=json.loads((ROOT/'records/uf1cash/wallet-rollover-authorization-v2.json').read_text(encoding='utf-8'))
        b=copy.deepcopy(b)
        d=next(q for q in b['fights'] if q['blue']=='Tallison Teixeira')
        d['outcomeStatus']='REPORTED'
        d['reportedWinner']='Tallison Teixeira'
        with self.assertRaises(ValueError):
            active_summary(a,b,c,authorization)
    def test_no_profitability_claim(self):
        x=summary(*fixture())
        self.assertIsNone(x['profitabilityClaim'])
        self.assertFalse(x['evidence']['independentOfficialUfcstatsResultDetailVerified'])

if __name__=='__main__': unittest.main()
