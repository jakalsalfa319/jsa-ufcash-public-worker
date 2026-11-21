#!/usr/bin/env python3
"""UF1Cash virtual multi-market receipts. No real wagering or invented payouts."""
from __future__ import annotations
import copy
import json
import re
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from scripts.all_in_challenge import d,cents,fingerprint,quoted_decimal,timestamp,url_good
from scripts.uf1cash_challenge import prepare
from scripts.uf1cash_partial_settlement import partial_settlement

SCHEMA="UF1CASH_MULTI_MARKET_INPUT_V1"
FROZEN="UF1CASH_MULTI_MARKET_FROZEN_V1"
AUTO={
    "MONEYLINE","MATCH_RESULT_1X2","TOTALS_OVER_UNDER","HANDICAP_SPREAD",
    "BINARY_PROP","METHOD_OF_VICTORY","ROUND_RESULT","OUTRIGHT_WINNER",
    "F1_PODIUM","F1_TOP_N","HORSE_PLACE_FIXED","CRICKET_RUN_TOTAL",
    "RUGBY_WINNING_MARGIN","YES_NO"
}
MANUAL={
    "EACH_WAY","EXACTA","TRIFECTA","SUPERFECTA","ACCUMULATOR",
    "SAME_EVENT_BUILDER","ASIAN_HANDICAP","DEAD_HEAT","PARTIAL_WIN",
    "CASH_OUT","IN_PLAY"
}
SPORTS={"UFC","F1","RUGBY_UNION","HORSE_RACING","CRICKET"}

def _required(value,label):
    if not isinstance(value,str) or not value.strip():
        raise ValueError(label+" required")
    return value.strip()

def _ticket(x,now):
    if not isinstance(x,dict):raise ValueError("Invalid ticket")
    ident=_required(x.get("ticketId"),"Ticket ID")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{2,95}",ident):
        raise ValueError("Invalid ticket ID")
    source_event=_required(x.get("sourceEventId"),"Source event")
    sport=_required(x.get("sport"),"Sport")
    if sport not in SPORTS:raise ValueError("Unapproved sport")
    market=_required(x.get("marketType"),"Market")
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,79}",market):
        raise ValueError("Market type format invalid")
    selection=_required(x.get("selection"),"Selection")
    start=timestamp(x.get("eventStartsUTC"))
    if start<=now:raise ValueError("Event started before ticket freeze")
    prob=d(x.get("modelPSelection"))
    if not 0<prob<1:raise ValueError("Probability outside zero and one")
    contract=x.get("settlementContract")
    if not isinstance(contract,dict):raise ValueError("Explicit settlement contract required")
    kind=contract.get("grading")
    if kind not in ("FIXED_BINARY","MANUAL_REVIEW"):
        raise ValueError("Unknown settlement grading")
    if kind=="FIXED_BINARY" and market not in AUTO:
        raise ValueError("Unsupported or complex market requires MANUAL_REVIEW")
    if market in MANUAL and kind!="MANUAL_REVIEW":
        raise ValueError("Complex market requires manual settlement")
    if not url_good(contract.get("publishedRulesUrl")):
        raise ValueError("Published market rules HTTPS URL required")
    terms=_required(contract.get("specificTerms"),"Settlement terms")
    if len(terms)<24:raise ValueError("Settlement terms insufficient")
    if contract.get("supportsVoidRefund") is not True:
        raise ValueError("Void refund treatment required")
    quote=x.get("quote")
    if not isinstance(quote,dict):raise ValueError("Quoted fixed price required")
    quoted_decimal(quote)
    timestamp(quote.get("capturedAtUTC"))
    if not url_good(quote.get("sourceUrl")) or not _required(quote.get("sourceName"),"Quote source"):
        raise ValueError("Source-attributed quote required")
    weight=d(x.get("weight",1))
    if weight<=0:raise ValueError("Positive stake weight required")
    legs=x.get("legs")
    if market in ("ACCUMULATOR","SAME_EVENT_BUILDER"):
        if kind!="MANUAL_REVIEW" or not isinstance(legs,list) or not 2<=len(legs)<=24:
            raise ValueError("Combination requires two or more manually graded legs")
        if quote.get("offeredCombinedPrice") is not True:
            raise ValueError("Combination odds must be genuinely offered as a quoted price")
        if not url_good(x.get("jointProbabilityModelUrl")):
            raise ValueError("Combined joint model source required")
        for leg in legs:
            if not isinstance(leg,dict):raise ValueError("Invalid accumulator leg")
            for name in ("sourceEventId","marketType","selection","eventStartsUTC"):
                _required(leg.get(name),"Leg "+name)
            leg_start=timestamp(leg["eventStartsUTC"])
            if leg_start<=now or leg_start<start:
                raise ValueError("Combined ticket must freeze before earliest leg starts")
    elif legs:
        raise ValueError("Legs only permitted on explicitly combined markets")
    return {"ticketId":ident,"sourceEventId":source_event,"sport":sport,
      "marketType":market,"selection":selection,"eventStartsUTC":x["eventStartsUTC"],
      "modelPSelection":str(prob),"quote":copy.deepcopy(quote),
      "weight":str(weight),"grading":kind,"publishedRulesUrl":contract["publishedRulesUrl"],
      "specificTerms":terms,"legs":copy.deepcopy(legs) if legs else []}

def freeze(wallet,policy,data,now=None):
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if data.get("schema")!=SCHEMA:raise ValueError("Wrong market input schema")
    raw=data.get("tickets")
    if not isinstance(raw,list) or not raw:raise ValueError("Market tickets required")
    tickets=[_ticket(t,now) for t in raw]
    lookup={x["ticketId"]:x for x in tickets}
    if len(lookup)!=len(tickets):raise ValueError("Duplicate ticket IDs")
    converted=[{
      "eventId":x["ticketId"],"sport":x["sport"],"market":x["marketType"],
      "selection":x["selection"],"eventStartsUTC":x["eventStartsUTC"],
      "modelPSelection":x["modelPSelection"],"quote":x["quote"],"weight":x["weight"]
    } for x in tickets]
    round_input={k:data.get(k) for k in (
        "roundId","strategy","availableBankrollZAR",
        "modelSourceUrl","modelSha256","modelCapturedUTC")}
    round_input.update({
       "schema":"UFCASH_ALLIN_INPUT_V1","candidates":converted,
       "minEstimatedEV":data.get("minEstimatedEV",policy["minEstimatedEV"]),
       "maxQuoteAgeMinutes":data.get("maxQuoteAgeMinutes",policy["maxQuoteAgeMinutes"])
    })
    outcome=prepare(wallet,policy,round_input,now)
    receipt=outcome["receipt"]
    chosen={r["eventId"] for r in receipt["selections"]}
    wrapper={"schema":FROZEN,"roundId":data["roundId"],
      "frozenAtUTC":receipt["frozenAtUTC"],
      "sourceBalanceZAR":outcome["sourceBalanceZAR"],
      "allInDeployedZAR":receipt["deployedZAR"],"uncommittedZAR":receipt["uncommittedZAR"],
      "tickets":[lookup[i] for i in sorted(chosen)],
      "frozenReceipt":receipt,"realBetsPlaced":0,
      "bookmakerExecuted":False,"sourcesIndependentlyVerified":False,
      "note":"Research-only virtual ticket selection; not an authenticated sportsbook order."}
    wrapper["envelopeSha256"]=fingerprint(wrapper)
    return wrapper

def reconcile(envelope,results,now=None):
    content={k:v for k,v in envelope.items() if k!="envelopeSha256"}
    if envelope.get("schema")!=FROZEN or fingerprint(content)!=envelope.get("envelopeSha256"):
        raise ValueError("Tampered multi-market receipt")
    if envelope.get("realBetsPlaced")!=0 or envelope.get("bookmakerExecuted") is not False:
        raise ValueError("Real betting not supported")
    lookup={x["ticketId"]:x for x in envelope["tickets"]}
    expected={x["eventId"] for x in envelope["frozenReceipt"]["selections"]}
    if set(lookup)!=expected:raise ValueError("Ticket list disagrees with frozen receipt")
    cleaned=[];seen=set()
    if not isinstance(results,list):raise ValueError("Expected result list")
    for r in results:
        ident=r.get("ticketId")
        if ident not in lookup or ident in seen:raise ValueError("Unknown or duplicate result")
        seen.add(ident)
        state=r.get("status")
        if state not in ("WIN","LOSS","VOID","PENDING","DISPUTED"):
            raise ValueError("Unsupported settlement state")
        if lookup[ident]["grading"]=="MANUAL_REVIEW" and state in ("WIN","LOSS","VOID"):
            raise ValueError("Complex/manual market cannot automatically credit a payout")
        clean={"eventId":ident,"status":state}
        if state in ("WIN","LOSS","VOID"):
            if not url_good(r.get("sourceUrl")):raise ValueError("Missing result source")
            clean["sourceUrl"]=r["sourceUrl"]
            clean["observedAtUTC"]=r["observedAtUTC"]
        cleaned.append(clean)
    x=partial_settlement(envelope["frozenReceipt"],cleaned,now)
    return {"schema":"UF1CASH_MULTI_MARKET_PROVISIONAL_SETTLEMENT_V1",
      "roundId":envelope["roundId"],"sourceEnvelopeSha256":envelope["envelopeSha256"],
      "availableReportedPayoutZAR":x["currentlyAvailableFromPaidReturnsZAR"],
      "lockedUnresolvedStakeZAR":x["lockedUnresolvedOriginalStakesZAR"],
      "paidWinningGrossZAR":x["winningGrossCreditsZAR"],
      "losingStakesZAR":x["losingStakesZAR"],
      "voidRefundsZAR":x["voidRefundCreditsZAR"],
      "status":x["status"],"realBetsPlaced":0,
      "independentResultVerification":False,
      "note":"Reported outcomes only; verify result contents and market-specific payout terms before incorporating into audited performance."}
