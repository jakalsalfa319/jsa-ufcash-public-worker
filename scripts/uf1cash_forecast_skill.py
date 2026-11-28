#!/usr/bin/env python3
"""Score genuinely time-ordered, source-attributed binary forecasts.

Input rows are supplied evidence, not automatically authenticated by a URL.
No real-money performance, no prospective betting and no sportsbook execution.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime,timezone
import json
import math
import random
from pathlib import Path
from scripts.all_in_challenge import timestamp,url_good,d

SCHEMA="UF1CASH_BINARY_FORECAST_AUDIT_INPUT_V1"
REPORT="UF1CASH_BINARY_FORECAST_SKILL_REPORT_V1"
ACTIVE=("UFC","F1","RUGBY_UNION","HORSE_RACING","CRICKET")

def _text(value,label):
    if not isinstance(value,str) or not value.strip():
        raise ValueError(label+" required")
    return value.strip()

def _paired_baseline(rows, reps=1000):
    """Paired Brier difference; event-cluster bootstrap, descriptive only."""
    clusters=defaultdict(list)
    for p,y,q,event in rows:
        if q is not None:
            clusters[event].append(((p-y)**2,(q-y)**2))
    if not clusters:
        return None
    groups=[clusters[k] for k in sorted(clusters)]
    matched=[v for g in groups for v in g]
    n=len(matched)
    model=sum(a for a,b in matched)/n
    base=sum(b for a,b in matched)/n
    interval=None
    if len(groups)>=10:
        # Resample whole events; do not treat same-event markets as independent.
        totals=[(sum(a-b for a,b in g),len(g)) for g in groups]
        rng=random.Random(20261128)
        draws=[]
        for _ in range(reps):
            sampled=rng.choices(totals,k=len(totals))
            draws.append(sum(a for a,b in sampled)/sum(b for a,b in sampled))
        draws.sort()
        interval=[round(draws[int((reps-1)*q)],6) for q in (.025,.975)]
    return {"matchedRows":n,"matchedEvents":len(groups),
            "modelBrier":round(model,6),"baselineBrier":round(base,6),
            "pairedDifference":round(model-base,6),
            "eventBootstrap95Interval":interval,
            "intervalStatus":"DESCRIPTIVE_EVENT_BOOTSTRAP" if interval else "INSUFFICIENT_EVENTS",
            "baselineProvenanceIndependentlyVerified":False}

def _metrics(rows):
    n=len(rows)
    if not n:return None
    brier=sum((p-y)**2 for p,y,_,_ in rows)/n
    logloss=-sum(y*math.log(p)+(1-y)*math.log1p(-p) for p,y,_,_ in rows)/n
    baseline=[(q-y)**2 for p,y,q,_ in rows if q is not None]
    bins=[[] for _ in range(5)]
    for p,y,_,_ in rows:
        bins[min(4,int(p*5))].append((p,y))
    reliability=[]
    ece=0.0
    for i,items in enumerate(bins):
        if not items:continue
        avg_pred=sum(p for p,y in items)/len(items)
        actual=sum(y for p,y in items)/len(items)
        gap=abs(avg_pred-actual)
        ece+=len(items)*gap/n
        reliability.append({"bin":i+1,"count":len(items),"meanForecast":round(avg_pred,6),
                            "observedFrequency":round(actual,6),"gap":round(gap,6)})
    return {"count":n,"uniqueUnderlyingEvents":len({event for _,_,_,event in rows}),
            "meanBrierLoss":round(brier,6),"meanLogLoss":round(logloss,6),
            "expectedCalibrationError":round(ece,6),
            "baseRate":round(sum(y for p,y,_,_ in rows)/n,6),
            "baselineBrierLossOnAvailableMatchedRows":round(sum(baseline)/len(baseline),6) if baseline else None,
            "baselineMatchedCount":len(baseline),"calibrationBins":reliability,
            "pairedBaselineComparison":_paired_baseline(rows)}

def audit(payload,now=None):
    if not isinstance(payload,dict) or payload.get("schema")!=SCHEMA:
        raise ValueError("Unknown forecast audit schema")
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    data=payload.get("records")
    if not isinstance(data,list) or not 1<=len(data)<=10000:
        raise ValueError("At least one and at most 10000 records required")
    seen=set();all_rows=[];group=defaultdict(list)
    for item in data:
        if not isinstance(item,dict):
            raise ValueError("Malformed observation")
        sport=_text(item.get("sport"),"Sport")
        if sport not in ACTIVE:
            raise ValueError("Unapproved sport")
        event=_text(item.get("eventId"),"Event ID")
        market=_text(item.get("marketId"),"Market identity")
        selection=_text(item.get("selectionId"),"Selection identity")
        ident=(sport,event,market,selection)
        if ident in seen:raise ValueError("Duplicate scored event/market/selection")
        seen.add(ident)
        predicted=timestamp(item.get("predictedAtUTC"))
        starts=timestamp(item.get("eventStartsUTC"))
        observed=timestamp(item.get("resultObservedUTC"))
        if not predicted<starts<=observed<=now:
            raise ValueError("LOOKAHEAD_BLOCKED: forecast must precede event and result follow it")
        if not url_good(item.get("modelSnapshotUrl")) or not url_good(item.get("resultSourceUrl")):
            raise ValueError("Source-linked forecast and result evidence required")
        h=item.get("modelSha256")
        if not isinstance(h,str) or len(h)!=64 or any(c not in "0123456789abcdef" for c in h):
            raise ValueError("Immutable model SHA required")
        if item.get("resultStatus") != "FINAL_REVIEWED":
            raise ValueError("Only final reviewed results may be scored; pending and disputed are excluded")
        y=item.get("outcome")
        if type(y) is not int or y not in (0,1):
            raise ValueError("Outcome must be definite zero or one; pending/disputed excluded")
        p=float(d(item.get("modelProbability")))
        if not math.isfinite(p) or not 0<p<1:
            raise ValueError("Forecast probability must be between 0 and 1")
        raw=item.get("baselineProbability")
        baseline=None if raw is None else float(d(raw))
        if baseline is not None and not 0<baseline<1:
            raise ValueError("Baseline probability out of range")
        entry=(p,y,baseline,sport+":"+event)
        all_rows.append(entry)
        group[sport].append(entry)
    return {"schema":REPORT,"mode":"SCORE_SUPPLIED_PROSPECTIVE_RECORDS",
      "observationsScored":len(all_rows),"skill":_metrics(all_rows),
      "bySport":{sport:_metrics(group[sport]) for sport in ACTIVE},
      "duplicatesOrLookaheadAllowed":False,"disputedResultsAllowed":False,
      "sourceEvidenceIndependentlyAuthenticated":False,
      "profitableBettingEdgeEstablished":False,"realBetsPlaced":0,
      "note":"A good Brier score does not establish positive expected return or verified source truth. Compare only to matched independently timestamped baselines and withheld events."}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=audit(json.loads(a.input.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False,allow_nan=False)
        f.write("\n")
    print(json.dumps({"scored":result["observationsScored"],"realBets":0}))

if __name__=="__main__":main()
