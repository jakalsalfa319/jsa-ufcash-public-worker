#!/usr/bin/env python3
"""Expose settled virtual returns while other all-in selections are still pending.

Reuses the existing fingerprint, date/status and no-real-money checks in settle_round.
Never treats a disputed wager as a paid ticket or reports verified profit.
"""
from __future__ import annotations
from datetime import datetime
from scripts.all_in_challenge import settle_round, cents, zar

SCHEMA = "UF1CASH_PARTIAL_VIRTUAL_SETTLEMENT_V1"

def partial_settlement(receipt:dict, outcomes:list, now:datetime|None=None)->dict:
    old=settle_round(receipt, outcomes, now)
    if receipt.get('status')!='ALL_IN_FROZEN':
        raise ValueError('Only a frozen fully staked round can be reconciled')
    if receipt.get('uncommittedZAR')!='0.00' or receipt.get('deployedZAR')!=receipt.get('openingBalanceZAR'):
        raise ValueError('All-in round must have zero uncommitted cash')
    available=pending=credited=losses=voids=0
    for r in old['reports']:
        state=r['status'];stake=cents(r['stakeZAR'])
        payout=r['scenarioReturnZAR']
        if state in ('PENDING','DISPUTED'):
            if payout is not None:
                raise ValueError('Pending/disputed payout cannot be credited')
            pending+=stake
        elif state in ('WIN','LOSS','VOID'):
            if payout is None:raise ValueError('Decisive settled result must have a return')
            amount=cents(payout);available+=amount
            if state=='WIN':credited+=amount
            elif state=='LOSS':losses+=stake
            else:voids+=amount
        else:raise ValueError('Unknown result status')
    if not pending and available != cents(old['nextAvailableBalanceZAR']):
        raise ValueError('Partial settlement disagrees with original final reconciliation')
    if pending and old['nextAvailableBalanceZAR'] is not None:
        raise ValueError('Unresolved round incorrectly marked fully settled')
    return {'schema':SCHEMA,'roundId':receipt['roundId'],
       'sourceReceiptSha256':receipt['receiptSha256'],
       'originalOpeningVirtualZAR':receipt['openingBalanceZAR'],
       'previouslyFullyCommittedVirtualZAR':receipt['deployedZAR'],
       'currentlyAvailableFromPaidReturnsZAR':zar(available),
       'lockedUnresolvedOriginalStakesZAR':zar(pending),
       'winningGrossCreditsZAR':zar(credited),
       'losingStakesZAR':zar(losses),
       'voidRefundCreditsZAR':zar(voids),
       'completed':pending==0,
       'status':'PARTIALLY_PAID_PENDING_STAKES_LOCKED' if pending else 'FULLY_RECONCILED_PROVISIONAL',
       'canReusePaidReturnsForNewFullyStakedVirtualRound':available>0,
       'usableZARForNextAllInRound':zar(available),
       'notAnExecutedBookmakerTicket':True,
       'priceAvailabilityIndependentlyVerified':False,
       'outcomeSourceContentsIndependentlyVerified':False,
       'verifiedProspectiveProfitZAR':None,
       'realFundsZAR':'0.00',
       'note':'Provisional virtual arithmetic only; do not count unsettled stake as available capital or backdate scenario entries.'}
