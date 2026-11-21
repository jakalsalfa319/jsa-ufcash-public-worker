#!/usr/bin/env python3
"""UFCash all-in VIRTUAL ZAR round ledger. NEVER real betting.

Prospective rounds require genuine point-in-time model and price evidence.
This file accepts inputs; it does NOT independently verify their contents.
Retrospective examples are kept in a separate function/report.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

INPUT = "UFCASH_ALLIN_INPUT_V1"
FROZEN = "UFCASH_ALLIN_FROZEN_V1"
RESULT = "UFCASH_ALLIN_RESULT_V1"
CENT = Decimal("0.01")


def d(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a number")
    try:
        value = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Invalid numeric value") from exc
    if not value.is_finite():
        raise ValueError("Not finite")
    return value


def cents(value):
    result = d(value) * 100
    if result != result.to_integral_value():
        raise ValueError("ZAR amounts must be whole cents")
    return int(result)


def zar(c):
    if type(c) is not int:
        raise ValueError("Expected integer cents")
    return str((Decimal(c) / 100).quantize(CENT))


def cash(value):
    return d(value).quantize(CENT, rounding=ROUND_HALF_UP)


def timestamp(value):
    try:
        out = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("Invalid ISO UTC timestamp") from exc
    if out.tzinfo is None or out.utcoffset() is None:
        raise ValueError("Timezone required")
    return out.astimezone(timezone.utc)


def date_text(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def url_good(value):
    if not isinstance(value, str):
        return False
    try:
        v = urlparse(value)
        return v.scheme == "https" and bool(v.hostname) and bool(v.path) and not v.username and not v.password
    except ValueError:
        return False


def odds_to_decimal(american):
    if type(american) is not int or abs(american) < 100:
        raise ValueError("Moneyline must be an integer outside (-100,+100)")
    return Decimal("1") + (d(american)/100 if american > 0 else 100/-d(american))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def weights_split(total_cents, weights):
    """Largest remainder cents split: every cent deployed, deterministic ties."""
    if not isinstance(weights, list) or not weights:
        raise ValueError("Weights required")
    ws = [d(v) for v in weights]
    if any(w <= 0 for w in ws):
        raise ValueError("All weights must be positive")
    if total_cents < len(ws):
        raise ValueError("Insufficient cents for positive stakes")
    total_w = sum(ws)
    raw = [d(total_cents)*w/total_w for w in ws]
    base = [int(x) for x in raw]
    left = total_cents-sum(base)
    if left > 0:
        order = sorted(range(len(ws)), key=lambda i: (-(raw[i]-base[i]), i))
        for i in order[:left]:
            base[i]+=1
    if sum(base)!=total_cents or min(base)<1:
        raise ValueError("Allocation failed")
    return base


def plan_round(data, now=None):
    """Make a new pre-event 100%-exposure R0 round receipt, or ABSTAIN.

    A local clock + SHA do not independently authenticate sportsbook quotes.
    Publish the receipt to timestamped GitHub CI before games for prospective evidence.
    """
    now = now or datetime.now(timezone.utc)
    now = now.astimezone(timezone.utc)
    if data.get("schema") != INPUT:
        raise ValueError("Unknown input schema")
    balance = cents(data["availableBankrollZAR"])
    if balance <= 0:
        raise ValueError("BANKRUPT: no funds and no new credit/top-up")
    if not isinstance(data.get("roundId"), str) or not data["roundId"].strip():
        raise ValueError("Round id required")
    if data.get("strategy") not in ("SINGLE", "BASKET"):
        raise ValueError("Strategy SINGLE or BASKET required")
    if not url_good(data.get("modelSourceUrl")) or not isinstance(data.get("modelSha256"), str) or len(data["modelSha256"])!=64 or any(x not in "0123456789abcdef" for x in data["modelSha256"]):
        raise ValueError("Pre-event forecast URL and SHA256 required")
    model_time = timestamp(data["modelCapturedUTC"])
    if model_time > now:
        raise ValueError("Model timestamp in the future")
    if d(data.get("minEstimatedEV", "0.03")) < 0:
        raise ValueError("Negative EV threshold")
    min_ev = d(data.get("minEstimatedEV", "0.03"))
    max_quote_minutes = d(data.get("maxQuoteAgeMinutes", "120"))
    if not (0 < max_quote_minutes <= 1440):
        raise ValueError("Quote age limit out of range")
    selections = data.get("candidates")
    if not isinstance(selections, list) or not selections:
        raise ValueError("At least one candidate required")
    ids, qualified, skipped = set(), [], []
    for candidate in selections:
        eid = candidate.get("eventId")
        if not isinstance(eid, str) or not eid.strip() or eid in ids:
            raise ValueError("Missing/duplicate event identity")
        ids.add(eid)
        start = timestamp(candidate["eventStartsUTC"])
        if start <= now:
            skipped.append({"eventId":eid,"reason":"ALREADY_STARTED"})
            continue
        quote = candidate.get("quote")
        if quote is None:
            skipped.append({"eventId":eid,"reason":"NO_QUOTE"})
            continue
        captured = timestamp(quote["capturedAtUTC"])
        if captured < model_time or captured > now or captured >= start:
            raise ValueError("Quote chronology invalid")
        if (now-captured).total_seconds() > float(max_quote_minutes*60):
            skipped.append({"eventId":eid,"reason":"STALE_QUOTE"})
            continue
        if not url_good(quote.get("sourceUrl")) or not quote.get("sourceName"):
            skipped.append({"eventId":eid,"reason":"UNATTRIBUTED_QUOTE"})
            continue
        odds = odds_to_decimal(quote["americanOdds"])
        if candidate.get("modelPSelection") is None:
            skipped.append({"eventId":eid,"reason":"NO_MODEL_PROBABILITY"})
            continue
        p = d(candidate["modelPSelection"])
        if not (0<p<1):
            raise ValueError("Invalid model probability")
        ev = p*odds-1
        if ev < min_ev:
            skipped.append({"eventId":eid,"reason":"BELOW_EV_GATE"})
            continue
        qualified.append({"eventId":eid,"sport":candidate.get("sport","unknown"),
                          "market":candidate.get("market","winner"),
                          "selection":candidate["selection"],
                          "eventStartsUTC":date_text(start),
                          "modelPSelection":str(p), "oddsAmerican":quote["americanOdds"],
                          "decimalOdds":str(odds),"modelEstimatedEV":str(ev),
                          "quoteSource":quote["sourceName"],"quoteUrl":quote["sourceUrl"],
                          "quoteCapturedUTC":date_text(captured),
                          "weight":candidate.get("weight",1)})
    if data["strategy"] == "SINGLE" and qualified:
        qualified = [max(qualified,key=lambda q:(d(q["modelEstimatedEV"]),q["eventId"]))]
    if qualified:
        stakes = weights_split(balance,[q.pop("weight") for q in qualified])
        for q, stake in zip(qualified,stakes):
            q["stakeZAR"] = zar(stake)
        status, committed, available = "ALL_IN_FROZEN", balance, 0
    else:
        status, committed, available = "ABSTAIN_NO_QUALIFIED_MARKET", 0, balance
    receipt = {"schema":FROZEN,"roundId":data["roundId"],
       "challenge":"R2000_NO_TOPUPS_ALL_IN", "mode":"FORWARD_PRE_EVENT_REFERENCE_ONLY",
       "frozenAtUTC":date_text(now),"strategy":data["strategy"],
       "openingBalanceZAR":zar(balance), "deployedZAR":zar(committed),
       "uncommittedZAR":zar(available),"status":status,"selections":qualified,
       "skipped":skipped,"modelCapturedUTC":date_text(model_time),
       "modelSourceUrl":data["modelSourceUrl"],"modelSha256":data["modelSha256"],
       "minEstimatedEV":str(min_ev),"realFundsUsedZAR":"0.00","realBetsPlaced":0,
       "isVerifiedExecutableQuote":False,"preEventPublicationExternallyVerified":False,
       "note":"SHA proves receipt integrity only, not source truth or an authenticated bookmaker quote. R0 simulation only."}
    receipt["receiptSha256"] = fingerprint(receipt)
    return receipt


def settle_round(receipt, outcomes, now=None):
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    base = {k:v for k,v in receipt.items() if k!="receiptSha256"}
    if receipt.get("schema")!=FROZEN or fingerprint(base)!=receipt.get("receiptSha256"):
        raise ValueError("Original all-in receipt invalid/tampered")
    if receipt["realBetsPlaced"] != 0:
        raise ValueError("Real bets must never occur")
    if receipt["status"] != "ALL_IN_FROZEN":
        raise ValueError("No open all-in round to settle")
    expected = {x["eventId"] for x in receipt["selections"]}
    observed = {}
    for row in outcomes:
        eid = row.get("eventId")
        if eid not in expected or eid in observed:
            raise ValueError("Unrecognized or duplicate result")
        status = row.get("status")
        if status not in ("WIN", "LOSS", "VOID", "PENDING", "DISPUTED"):
            raise ValueError("Bad result status")
        if status not in ("PENDING","DISPUTED") and not url_good(row.get("sourceUrl")):
            raise ValueError("Results source URL required")
        if status in ("WIN","LOSS","VOID"):
            observed_at = timestamp(row["observedAtUTC"])
            starts_at = timestamp(next(x["eventStartsUTC"] for x in receipt["selections"] if x["eventId"] == eid))
            if observed_at < starts_at or observed_at > now:
                raise ValueError("Result timestamp outside permissible post-start window")
        observed[eid] = row
    payout_c = 0
    reports=[]
    unsettled=False
    for item in receipt["selections"]:
        row=observed.get(item["eventId"],{"status":"PENDING"})
        status=row["status"]
        stake=cents(item["stakeZAR"])
        if status in ("PENDING","DISPUTED"):
            unsettled=True
            payout=None
        elif status=="VOID":
            payout=stake
        elif status=="LOSS":
            payout=0
        else:
            payout=int((cash(d(item["stakeZAR"])*d(item["decimalOdds"]))*100))
        if payout is not None:
            payout_c+=payout
        reports.append({"eventId":item["eventId"],"selection":item["selection"],
             "status":status,"stakeZAR":item["stakeZAR"],
             "scenarioReturnZAR":zar(payout) if payout is not None else None,
             "resultSourceUrl":row.get("sourceUrl"),"sourceContentIndependentlyVerified":False})
    completed=not unsettled
    return {"schema":RESULT,"originalReceiptSha256":receipt["receiptSha256"],
      "roundId":receipt["roundId"],"status":"PROVISIONAL_SCENARIO_COMPLETE" if completed else "OPEN_DISPUTED_OR_PENDING",
      "openingBalanceZAR":receipt["openingBalanceZAR"],
      "lockedPendingZAR":receipt["deployedZAR"] if unsettled else "0.00",
      "nextAvailableBalanceZAR":zar(payout_c) if completed else None,
      "provisionalPayoutTotalZAR":zar(payout_c),
      "provisionalNetZAR":zar(payout_c-cents(receipt["openingBalanceZAR"])) if completed else None,
      "reports":reports,"realBetsPlaced":0,"verifiedProspectiveProfitZAR":None,
      "note":"Claimed results/quotes; independent official content and executable quote availability not verified. Cannot reuse any balance while pending."}


def historical_qatar_allin(data,bankroll="2000",strategy="BASKET",min_ev="0.03"):
    """Retrospective WHAT IF only: use prior recorded model/third-party prices; no frozen tickets."""
    start=cents(bankroll)
    if start<=0: raise ValueError("Opening bankroll must be positive")
    if strategy not in ("SINGLE","BASKET"): raise ValueError("SINGLE/BASKET only")
    if data.get("schema")!="UFCASH_RETROSPECTIVE_INPUT_V1": raise ValueError("Wrong historical input")
    seen=set(); selections=[]
    for row in data["fights"]:
        key=tuple(sorted([row["red"].casefold(),row["blue"].casefold()]))
        if key in seen: raise ValueError("Duplicate matchup")
        seen.add(key)
        p=d(row["modelPRed"])
        if not 0<p<1: raise ValueError("Bad model probability")
        sides=[(row["red"],p,odds_to_decimal(row["redAmerican"]),row["redAmerican"]),
               (row["blue"],1-p,odds_to_decimal(row["blueAmerican"]),row["blueAmerican"])]
        chosen=max(sides,key=lambda x:x[1]*x[2]-1)
        selection,winp,dec,american=chosen
        ev=winp*dec-1
        if ev < d(min_ev): continue
        status=row["outcomeStatus"]
        if status not in ("REPORTED","DISPUTED","PENDING","NO_CONTEST","DRAW","CANCELLED","REPLACED"):
            raise ValueError("Unsupported result")
        if status=="REPORTED" and row.get("reportedWinner") not in (row["red"],row["blue"]):
            raise ValueError("Invalid result")
        if status!="REPORTED" and row.get("reportedWinner") is not None:
            raise ValueError("Non-decided winner supplied")
        selections.append({"event":row["red"]+" vs "+row["blue"],"selection":selection,
                 "modelProbability":str(winp),"americanOdds":american,"decimalOdds":str(dec),
                 "modelEstimatedEV":str(ev),"reportedStatus":status,"reportedWinner":row.get("reportedWinner")})
    selections.sort(key=lambda x:(-d(x["modelEstimatedEV"]),x["event"]))
    if strategy=="SINGLE" and selections:
        selections=selections[:1]
    stakes=weights_split(start,[1]*len(selections)) if selections else []
    known_payout_c=0; unknown=[]
    for item,stake_c in zip(selections,stakes):
        item["virtualStakeZAR"]=zar(stake_c)
        status=item["reportedStatus"]
        if status=="REPORTED":
            payout=int(cash(d(item["virtualStakeZAR"])*d(item["decimalOdds"]))*100) if item["selection"]==item["reportedWinner"] else 0
            known_payout_c+=payout
            item["scenarioReturnZAR"]=zar(payout)
            item["scenarioResult"]="WIN" if payout else "LOSS"
        else:
            item["scenarioReturnZAR"]=None
            item["scenarioResult"]="UNRESOLVED_"+status
            unknown.append(item)
    upper=known_payout_c+sum(int(cash(d(x["virtualStakeZAR"])*d(x["decimalOdds"]))*100) for x in unknown)
    return {"schema":"UFCASH_ALLIN_HISTORICAL_V1","classification":"POST_EVENT_WHAT_IF_NOT_PROSPECTIVE",
     "eventId":data["eventId"],"strategy":strategy,"startingBalanceZAR":zar(start),
     "exposureZAR":zar(sum(stakes)),"uncommittedZAR":zar(start-sum(stakes)),
     "selectionCount":len(selections),"quotedOddsAuthenticityIndependent":False,
     "minimumEVChosenRetrospectively":str(d(min_ev)),
     "reportedKnownPayoutZAR":zar(known_payout_c),
     "finalBankrollIfAllUnresolvedLoseZAR":zar(known_payout_c),
     "finalBankrollIfAllUnresolvedWinZAR":zar(upper),
     "realFundsUsedZAR":"0.00","realBetsPlaced":0,
     "observedReturnsVerified":False,"prospectiveROI":None,
     "quoteSource":data.get("reportedPreEventOddsSource"),
     "modelSource":data.get("frozenPredictionSource"),
     "selections":selections,
     "note":"Selection threshold and all-in policy devised after results. Quotes are historical reported prices, not authenticated offers. Disputes remain unresolved."}


def write_new(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8") as f:
        json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
        f.write("\n")


def cli():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    for action in ("freeze","settle","historical"):
        s=sub.add_parser(action)
        s.add_argument("--input",type=Path,required=True)
        s.add_argument("--output",type=Path,required=True)
        if action=="historical":
            s.add_argument("--bankroll",default="2000")
            s.add_argument("--strategy",choices=["SINGLE","BASKET"],default="BASKET")
    a=p.parse_args()
    data=json.loads(a.input.read_text(encoding="utf-8"))
    if a.action=="freeze":
        report=plan_round(data)
    elif a.action=="settle":
        report=settle_round(data["receipt"],data["outcomes"])
    else:
        report=historical_qatar_allin(data,a.bankroll,a.strategy)
    write_new(a.output,report)
    print(json.dumps({k:report.get(k) for k in ("schema","status","selectionCount","startingBalanceZAR","finalBankrollIfAllUnresolvedLoseZAR","finalBankrollIfAllUnresolvedWinZAR","receiptSha256") if k in report},indent=2))

if __name__=="__main__":cli()
