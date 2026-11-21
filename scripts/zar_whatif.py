#!/usr/bin/env python3
"""UFCash R0 retrospective value screen: ZAR cashflows, NO historical tickets.

Explicitly post-hoc: publishing this today cannot manufacture a prospective bet.
All odds are reported reference prices, never user-specific executable quotes.
"""
from __future__ import annotations
import argparse
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path

D = lambda x: Decimal(str(x))
CENT = D('0.01')
def money(x): return x.quantize(CENT, rounding=ROUND_HALF_UP)

def decimal_odds(american):
    if isinstance(american, bool) or not isinstance(american, int) or abs(american) < 100:
        raise ValueError('Invalid American moneyline')
    return D(1) + (D(american) / D(100) if american > 0 else D(100) / -D(american))

def calculate(data, starting_bankroll='1000', stake_fraction='0.01', min_ev='0.03', total_cap='0.05'):
    """Return explicit scenario accounting, not authenticated tickets or realized ROI."""
    bankroll, fraction, threshold, cap = map(D, (starting_bankroll, stake_fraction, min_ev, total_cap))
    if not (bankroll > 0 and D(0) < fraction <= D('0.01') and
            fraction <= cap <= D('0.05') and D(0) <= threshold <= D(1)):
        raise ValueError('Invalid paper-money rules')
    if data.get('schema') != 'UFCASH_RETROSPECTIVE_INPUT_V1' or not data.get('frozenPredictionSource') or not data.get('reportedPreEventOddsSource'):
        raise ValueError('Missing provenance')
    rows = data.get('fights')
    if not isinstance(rows, list) or not rows:
        raise ValueError('No fights')
    stake = money(bankroll * fraction)
    if stake <= 0: raise ValueError('Stake rounds to zero')
    seen, screen = set(), []
    for f in rows:
        pair = (f['red'].casefold(), f['blue'].casefold())
        if pair in seen: raise ValueError('Duplicate fight')
        seen.add(pair)
        p = D(f['modelPRed'])
        if not D(0) < p < D(1): raise ValueError('Invalid model probability')
        d_red, d_blue = decimal_odds(f['redAmerican']), decimal_odds(f['blueAmerican'])
        options = [(p*d_red-D(1), f['red'], f['redAmerican'], d_red, p),
                   ((D(1)-p)*d_blue-D(1), f['blue'], f['blueAmerican'], d_blue, D(1)-p)]
        ev, selection, odds, dec, confidence = max(options, key=lambda v: v[0])
        status = f['outcomeStatus']
        winner = f.get('reportedWinner')
        if status not in ('REPORTED', 'DISPUTED', 'PENDING', 'NO_CONTEST', 'DRAW', 'CANCELLED', 'REPLACED'):
            raise ValueError('Bad outcome status')
        if (status == 'REPORTED') != (winner in (f['red'], f['blue'])):
            raise ValueError('Reported winner/status mismatch')
        screen.append({'fight': f['red']+' vs '+f['blue'], 'red': f['red'], 'blue':f['blue'],
                'modelPRed': float(p), 'modelFavorite': f['red'] if p >= D('.5') else f['blue'],
                'marketFavorite': f['red'] if d_red <= d_blue else f['blue'],
                'selection':selection, 'americanOdds':odds, 'decimalOdds':float(dec),
                'modelSelectionP':float(confidence), 'modelEstimatedEV':float(ev),
                'outcomeStatus':status, 'reportedWinner':winner,
                'qualifies':ev>=threshold, '_EV':ev, '_DECIMAL':dec})
    eligible = sorted([i for i,r in enumerate(screen) if r['qualifies']],
                      key=lambda i:(-screen[i]['_EV'],i))
    cap_amount = money(bankroll*cap)
    spent = D(0)
    for i in eligible:
        r = screen[i]
        if spent+stake>cap_amount:
            r['qualifies']=False
            r['skipReason']='MAX_EVENT_EXPOSURE'
        else:
            spent+=stake
            r['hypotheticalStakeZAR']=float(stake)
    settled_net, pending_stake, reported_wins, reported_losses = D(0), D(0), 0, 0
    reported_correct, market_correct, reported_count = 0,0,0
    for r in screen:
        status,winner=r['outcomeStatus'],r['reportedWinner']
        if status=='REPORTED':
            reported_count += 1
            reported_correct += int(r['modelFavorite']==winner)
            market_correct += int(r['marketFavorite']==winner)
        if 'hypotheticalStakeZAR' not in r:
            r['ticketState']='NO_SCENARIO_STAKE'
            r['hypotheticalNetZAR']=None
        elif status=='REPORTED':
            net = money(stake*(r['_DECIMAL']-D(1))) if r['selection']==winner else -stake
            settled_net+=net
            r['ticketState']='REPORTED_WIN' if net>0 else 'REPORTED_LOSS'
            r['hypotheticalNetZAR']=float(net)
            if net>0: reported_wins+=1
            else: reported_losses+=1
        else:
            pending_stake+=stake
            r['ticketState']='UNSETTLED_'+status
            r['hypotheticalNetZAR']=None
        del r['_EV']; del r['_DECIMAL']
    undecided=[r for r in screen if r['ticketState'].startswith('UNSETTLED')]
    worst = settled_net-pending_stake
    best = settled_net + sum((money(stake*(decimal_odds(r['americanOdds'])-1)) for r in undecided), D(0))
    return {
        'schema':'UFCASH_ZAR_RETROSPECTIVE_WHATIF_V1',
        'eventId':data['eventId'], 'classification':'POST_HOC_HYPOTHETICAL_NOT_FORWARD_PAPER_TRADING',
        'initialVirtualBankrollZAR':float(bankroll), 'stakeFraction':float(fraction),
        'stakePerSelectionZAR':float(stake), 'maxExposureZAR':float(cap_amount),
        'modelMinimumEstimatedEV':float(threshold), 'modelFrozenSource':data['frozenPredictionSource'],
        'reportedReferencePriceSource':data['reportedPreEventOddsSource'],
        'quoteAvailabilityToUserVerified':False, 'ordersFrozenBeforeFights':False,
        'realBetsPlaced':0, 'realFundsUsedZAR':0,
        'scenarioSelectionCount':sum('hypotheticalStakeZAR' in r for r in screen),
        'reportedScenarioWins':reported_wins, 'reportedScenarioLosses':reported_losses,
        'unsettledScenarioSelections':len(undecided),
        'stakedHypotheticalZAR':float(spent), 'unsettledStakeZAR':float(pending_stake),
        'hypotheticalNetFromReportedDecisiveZAR':float(settled_net),
        'finalBalanceIfAllUnsettledLoseZAR':float(money(bankroll+worst)),
        'finalBalanceIfAllUnsettledWinZAR':float(money(bankroll+best)),
        'reportedModelAccuracy':{'correct':reported_correct,'n':reported_count,
               'percent':round(100*reported_correct/reported_count,2) if reported_count else None},
        'reportedMarketFavoriteAccuracy':{'correct':market_correct,'n':reported_count,
               'percent':round(100*market_correct/reported_count,2) if reported_count else None},
        'verifiedProspectiveROI':None,
        'notes':['This policy was reconstructed after the fights; do not cite as a forward result.',
                 'Historical sportsbook quotes were independently reported, not executable fill receipts.',
                 'DISPUTED bouts stay unsettled even when one outcome would increase scenario profit.',
                 'Reported secondary-media results are not official UFCStats settlements.',
                 'No real money, bookmaker accounts, or wagering API access.'],
        'selections':screen
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--bankroll',default='1000')
    p.add_argument('--fraction',default='0.01')
    p.add_argument('--minimum-ev',default='0.03')
    a=p.parse_args()
    result=calculate(json.loads(a.input.read_text(encoding='utf-8')),
                     a.bankroll,a.fraction,a.minimum_ev)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2,ensure_ascii=False,allow_nan=False)
        f.write('\n')
    print(json.dumps({k:result[k] for k in ('initialVirtualBankrollZAR','scenarioSelectionCount','hypotheticalNetFromReportedDecisiveZAR','finalBalanceIfAllUnsettledLoseZAR','finalBalanceIfAllUnsettledWinZAR')},indent=2))

if __name__=='__main__': main()
