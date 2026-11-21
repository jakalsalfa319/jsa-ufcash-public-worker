#!/usr/bin/env python3
"""UF1Cash: deterministic, source-backed, research-only ZAR ledger summary.

A retrospective replay is *never* promoted into the genuine prospective wallet.
Existing frozen forecasts, model checkpoint, and challenge genesis are read only.
"""
from __future__ import annotations
import argparse
import json
from decimal import Decimal
from pathlib import Path
from scripts.all_in_challenge import historical_qatar_allin, cents

SCHEMA = 'UF1CASH_VIRTUAL_LEDGER_V1'
REVIEW_SCHEMA = 'UF1CASH_QATAR_EVIDENCE_REVIEW_V1'
FOCUS = {'UFC': 75, 'F1': 25}
BENCH = ('rugby_union', 'horse_racing', 'cricket', 'tennis', 'basketball', 'football', 'other_motorsport')

def summary(genesis:dict, source:dict, review:dict)->dict:
    if genesis.get('schema') != 'UFCASH_VIRTUAL_ZAR_GENESIS_V1':
        raise ValueError('Unexpected wallet genesis schema')
    if genesis.get('openingBankrollZAR') != '2000.00' or genesis.get('historicalWhatIfsCountAsBalanceChanges') is not False:
        raise ValueError('Opening wallet must remain a distinct R2000 prospective balance')
    if any(genesis.get(k) != v for k,v in {'availableVirtualZAR':'2000.00','stakedVirtualZAR':'0.00','prospectiveRoundsCompleted':0,'prospectiveSelectionsPlaced':0,'topupsAllowed':False}.items()):
        raise ValueError('Wallet has changed; do not silently reuse genesis as current balance')
    if source.get('schema') != 'UFCASH_RETROSPECTIVE_INPUT_V1' or source.get('eventId') != 'ufc-qatar-2026-11-21':
        raise ValueError('Unexpected original retrospective input')
    if review.get('schema') != REVIEW_SCHEMA or review.get('eventId') != source['eventId']:
        raise ValueError('Unrelated evidence review')
    if review['classification'] != 'SECONDARY_REPORTED_RESULTS_CONFLICT_REQUIRES_OFFICIAL_DETAIL':
        raise ValueError('Review must retain its provisional classification')
    details=review['outcomes']
    if not isinstance(details,list) or len(details)!=7:
        raise ValueError('Expected exactly seven reviewed bouts')
    names = {(f['red'],f['blue']) for f in source['fights']}
    if len(names)!=7 or {(r['red'],r['blue']) for r in details} != names:
        raise ValueError('Review does not match all seven original bouts')
    statuses={(r['red'],r['blue']):r for r in details}
    for f in source['fights']:
        r=statuses[(f['red'],f['blue'])]
        if r['ledgerStatus']!=f['outcomeStatus'] or r['reportedWinner']!=f['reportedWinner']:
            raise ValueError('Original input and evidence review disagree; append a versioned correction instead')
        if r['ledgerStatus']=='DISPUTED' and r['reportedWinner'] is not None:
            raise ValueError('Disputed result cannot be silently assigned a winner')
    single=historical_qatar_allin(source,'2000','SINGLE')
    basket=historical_qatar_allin(source,'2000','BASKET')
    for s in (single,basket):
        if s['classification'] != 'POST_EVENT_WHAT_IF_NOT_PROSPECTIVE' or s['exposureZAR']!='2000.00' or s['uncommittedZAR']!='0.00':
            raise ValueError('Historical replay is not a full R2000 what-if')
    if len(single['selections'])!=1 or len(basket['selections'])!=4:
        raise ValueError('Historical strategy selection changed')
    if sum(cents(s['virtualStakeZAR']) for s in basket['selections']) != 200000:
        raise ValueError('Basket does not commit every cent')
    if any(x['scenarioResult']=='WIN' and x['reportedStatus']!='REPORTED' for x in basket['selections']):
        raise ValueError('Disputed status cannot be considered a win')
    reported=[f for f in source['fights'] if f['outcomeStatus']=='REPORTED']
    if len(reported)!=6 or sum((Decimal(str(f['modelPRed']))>=Decimal('.5')) == (f['reportedWinner']==f['red']) for f in reported)!=5:
        raise ValueError('Known six-bout research score changed')
    def abbreviated(s):
        return {'classification':s['classification'], 'strategy':s['strategy'],
           'openingZAR':s['startingBalanceZAR'], 'totalSimulatedStakesZAR':s['exposureZAR'],
           'uncommittedZAR':s['uncommittedZAR'], 'selectionCount':s['selectionCount'],
           'reportedKnownGrossPayoutZAR':s['reportedKnownPayoutZAR'],
           'ifDisputedLosesFinalZAR':s['finalBankrollIfAllUnresolvedLoseZAR'],
           'ifDisputedWinsFinalZAR':s['finalBankrollIfAllUnresolvedWinZAR'],
           'ifDisputedLosesNetZAR':str((Decimal(s['finalBankrollIfAllUnresolvedLoseZAR'])-2000).quantize(Decimal('0.01'))),
           'ifDisputedWinsNetZAR':str((Decimal(s['finalBankrollIfAllUnresolvedWinZAR'])-2000).quantize(Decimal('0.01'))),
           'selections':[{k:x[k] for k in ('event','selection','americanOdds','virtualStakeZAR','reportedStatus','scenarioResult','scenarioReturnZAR')} for x in s['selections']]}
    out={
      'schema':SCHEMA, 'brand':'UF1Cash', 'operationalName':'J$A UF1Cash / UFCash legacy',
      'asOfUTC':review['reviewAsOfUTC'], 'currency':'ZAR',
      'developmentFocusPercent':FOCUS, 'developmentFocusIsNotStakeSplit':True,
      'eligibleForwardSports':['UFC','F1'],
      'researchBench':{name:'ON_HOLD_NO_ACTIVE_MODEL_OR_PAPER_SELECTION' for name in BENCH},
      'operatingMode':'RESEARCH_AND_IMAGINARY_MONEY_ONLY',
      'prospectiveWallet':{
        'genesisId':genesis['challengeId'], 'balanceAvailableZAR':'2000.00',
        'committedZAR':'0.00','realFundsZAR':'0.00','completedRounds':0,'validPreEventPaperSelections':0,
        'topUpsAllowed':False,'allInRule':'EVERY_ELIGIBLE_ACTIVE_ROUND_COMMITS_100_PERCENT_OR_ABSTAINS',
        'retrospectiveResultsChangeBalance':False,
        'status':'OPEN_AWAITING_FIRST_AUTHENTICATED_PRE_EVENT_ROUND'},
      'pastCardRecord':{
        'eventId':'ufc-qatar-2026-11-21','eventDate':'2026-11-21',
        'classification':'RETROSPECTIVE_RECONSTRUCTION_NOT_PRE_EVENT_PAPER_BETS',
        'referencePricesNotExecutable':True,
        'separateMutuallyExclusiveHypotheses':True,
        'originalFrozenPredictionsUrl':source['frozenPredictionSource'],
        'reportedPriceSourceUrl':source['reportedPreEventOddsSource'],
        'reportedFightSourceUrl':source['reportedResultSource'],
        'conflictingUfcHostedSourceUrl':source['disputeSource'],
        'recordedPaperBetsBeforeEvent':0, 'realBets':0,
        'reportedFightModelWinnerScore':{'correct':5,'eligible':6,'percent':'83.33','disputedExcluded':1},
        'disputedBout':'Shamil Gaziev vs Tallison Teixeira',
        'disputeStatus':'OFFICIAL_UFCSTATS_DETAIL_NOT_YET_VERIFIED_AND_SOURCES_CONFLICT',
        'basket':abbreviated(basket), 'singleAlternative':abbreviated(single),
        'liveChallengeBankrollAffected':False
       },
      'nextResearch':{
        'UFC':'Capture new pre-fight model probabilities, verified quotes, and public receipt before each future bout',
        'F1':'Validate historical F1 winner-market predictions; Qatar GP 27-29 November 2026 is calendar watch only',
        'noUnverifiedMarkets':'No paper selection until genuine forward probabilities and source prices exist'},
      'evidence':{
        'readme':'See docs/UF1CASH_OPERATING_RECORD.md',
        'reviewFile':'research/uf1cash-qatar-2026-11-21-evidence-v1.json',
        'independentOfficialUfcstatsResultDetailVerified':False,
        'sourceDisagreementPreserved':True},
      'profitabilityClaim':None,
      'note':'Retrospective win scenarios are NOT prospective profit. The UFCash model matched 5/6 reported, non-disputed bouts; a tiny sample does not prove outperformance.'
    }
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    root=a.repo_root
    data=summary(*[json.loads((root/path).read_text(encoding='utf-8')) for path in
      ('public/ufcash-r2000-allin-genesis.json',
       'research/2026-11-21-qatar-reference-input.json',
       'research/uf1cash-qatar-2026-11-21-evidence-v1.json')])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:
        json.dump(data,f,indent=2,ensure_ascii=False,allow_nan=False)
        f.write('\n')
    print(json.dumps({'status':'SAVED_RESEARCH_ONLY','walletZAR':data['prospectiveWallet']['balanceAvailableZAR'],
     'basketIfLoses':data['pastCardRecord']['basket']['ifDisputedLosesFinalZAR'],
     'basketIfWins':data['pastCardRecord']['basket']['ifDisputedWinsFinalZAR'],
     'noRealBets':True},indent=2))
if __name__=='__main__':main()
