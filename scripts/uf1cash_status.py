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
FOCUS = {'UFC': 50, 'F1': 12.5, 'RUGBY_UNION': 12.5, 'HORSE_RACING': 12.5, 'CRICKET': 12.5}
BENCH = ('tennis', 'basketball', 'football', 'other_motorsport')

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
      'eligibleForwardSports':['UFC','F1','RUGBY_UNION','HORSE_RACING','CRICKET'],
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
        'F1':'Validate historical F1 winner-market predictions; calendar and non-executable sources only',
        'RUGBY_UNION':'Three-way win/draw/loss predictions with confirmed match fixtures and fresh public fixed-odds board',
        'HORSE_RACING':'Complete declared field, fixed WIN quotes and scratchings checks before any paper decision',
        'CRICKET':'T20 winner incl. Super Over probabilities using permitted historical data and fresh odds',
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



def active_summary(genesis:dict, source:dict, review:dict, authorization:dict)->dict:
    """Authorize the historical basket as the active virtual wallet; do not fake pre-event bet timing."""
    if authorization.get('schema') != 'UF1CASH_USER_AUTHORIZED_RETROACTIVE_VIRTUAL_ROLLOVER_V2':
        raise ValueError('Missing user rollover authorization')
    if authorization.get('noPreEventBetReceipt') is not True or authorization.get('noRealWagers') is not True or authorization.get('noTopups') is not True:
        raise ValueError('Historical source cannot be marked a real pre-event bet or top-up')
    if authorization.get('roundId')!='ufc-qatar-2026-11-21' or authorization.get('strategy')!='BASKET':
        raise ValueError('Wrong historical scenario selected')
    out=summary(genesis,source,review)
    p=out['pastCardRecord']['basket']
    bets=p['selections']
    if len(bets)!=4 or sum(cents(x['virtualStakeZAR']) for x in bets)!=200000:
        raise ValueError('The four R500 stakes must consume entire R2000')
    winners=[x for x in bets if x['scenarioResult']=='WIN' and x['reportedStatus']=='REPORTED']
    pending=[x for x in bets if x['scenarioResult']=='UNRESOLVED_DISPUTED' and x['reportedStatus']=='DISPUTED']
    if len(winners)!=3 or len(pending)!=1 or pending[0]['scenarioReturnZAR'] is not None:
        raise ValueError('No disputed payout can be credited')
    paid=sum(cents(x['scenarioReturnZAR']) for x in winners)
    outstanding=sum(cents(x['virtualStakeZAR']) for x in pending)
    if paid!=cents(p['reportedKnownGrossPayoutZAR']) or paid!=307174 or outstanding!=50000:
        raise ValueError('Recomputed virtual balance inconsistent with source ledger')
    if not authorization.get('forwardUseOnlyAvailableCreditedBalance'):
        raise ValueError('Pending stake cannot be used again')
    out['schema']='UF1CASH_VIRTUAL_LEDGER_V2'
    out['ledgerRecordedOn']=authorization['recordedOnDate']
    out['currentBalanceZAR']='3071.74'
    out['currentVirtualPnLZAR']='1071.74'
    out['currentBalanceClassification']='USER_ADOPTED_RETROSPECTIVE_SIMULATION_NOT_AUTHENTICATED_PRE_EVENT_BETS'
    w=out['prospectiveWallet']
    w.update({'balanceAvailableZAR':'3071.74','committedZAR':'500.00',
              'retrospectiveResultsChangeBalance':True,'originIncludesRetrospectiveScenario':True,
              'retrospectiveSimulatedSelections':4,'pendingOriginalStakeZAR':'500.00',
              'possibleAdditionalDisputedPayoutZAR':'1325.00',
              'availableForNextQualifyingFullDeploymentZAR':'3071.74',
              'status':'USER_ADOPTED_RETROSPECTIVE_BALANCE_PENDING_DISPUTED_LEG'})
    out['pastCardRecord']['liveChallengeBankrollAffected']=True
    out['pastCardRecord']['rolloverTreatment']='USER_AUTHORIZED_RETROSPECTIVE_CREDIT_NOT_PROSPECTIVE'
    out['evidence']['walletRolloverAuthority']='records/uf1cash/wallet-rollover-authorization-v2.json'
    out['evidence']['legacyVersionedStatus']='records/uf1cash/status-snapshot-v1.json'
    out['walletMovement']={'startingBalanceZAR':'2000.00','fourHypotheticalStakesZAR':'2000.00',
      'creditedReportedGrossPayoutsZAR':'3071.74','unsettledStakePreviouslyDebitedZAR':'500.00',
      'workingAvailableZAR':'3071.74','profitAgainstOpeningZAR':'1071.74',
      'ifDisputedWinsExtraPayoutZAR':'1325.00','ifDisputedLosesExtraPayoutZAR':'0.00',
      'sourceEventDate':'2026-11-21','rolloverAuthorizedOn':'2026-11-22',
      'originallyFrozenPaperBets':0,'realWagers':0}
    out['note']='Working virtual R3071.74 is user-adopted retrospective UFC Qatar basket arithmetic, not authenticated prospective betting profit. Three reported winners credited; disputed Teixeira hypothetical return not credited. Future valid paper trades start from current available balance.'
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    root=a.repo_root
    data=active_summary(*[json.loads((root/path).read_text(encoding='utf-8')) for path in
      ('public/ufcash-r2000-allin-genesis.json',
       'research/2026-11-21-qatar-reference-input.json',
       'research/uf1cash-qatar-2026-11-21-evidence-v1.json',
       'records/uf1cash/wallet-rollover-authorization-v2.json')])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:
        json.dump(data,f,indent=2,ensure_ascii=False,allow_nan=False)
        f.write('\n')
    print(json.dumps({'status':'SAVED_RESEARCH_ONLY','walletZAR':data['prospectiveWallet']['balanceAvailableZAR'],
     'basketIfLoses':data['pastCardRecord']['basket']['ifDisputedLosesFinalZAR'],
     'basketIfWins':data['pastCardRecord']['basket']['ifDisputedWinsFinalZAR'],
     'noRealBets':True},indent=2))
if __name__=='__main__':main()
