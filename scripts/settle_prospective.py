#!/usr/bin/env python3
"""Score an earlier UFC research snapshot against independently sourced outcomes.

Use only AFTER the event is complete. A snapshot is never rewritten.
CSV: red,blue,outcome_red,source_url,verified_at_utc
outcome_red = 1/0 for decisive bouts, DRAW or NC when no decisive outcome.
No bookmaker implied odds, ROI or financial claims are calculated.
"""
import argparse
import csv
import datetime as dt
import json
import math
import unicodedata
import re
from pathlib import Path

from scripts.prospective_journal import digest, normalize, can_freeze


def metrics(points):
    n=len(points)
    if not n:return {"count":0,"correct":None,"accuracy":None,"brier":None,"logloss":None}
    outcomes=[int(y) for p,y in points]
    probs=[float(p) for p,y in points]
    hits=sum((p>=.5)==bool(y) for p,y in zip(probs,outcomes))
    brier=sum((p-y)**2 for p,y in zip(probs,outcomes))/n
    logloss=-sum(y*math.log(max(1e-10,p))+(1-y)*math.log(max(1e-10,1-p)) for p,y in points)/n
    return {"count":n,"correct":hits,"accuracy":hits/n,"brier":brier,"logloss":logloss}


def reconcile(snapshot, outcomes, verified_at):
    if snapshot.get("status")!="PRE_EVENT_RESEARCH_ONLY":
        raise ValueError("No genuine pre-event snapshot")
    if can_freeze(snapshot["eventDate"],verified_at):
        raise ValueError("Cannot score results before the event has begun")
    if len(snapshot.get("predictions",[]))!=7 or len(outcomes)!=7:
        raise ValueError("Expected seven snapshot bouts and seven official bout rows")
    indexed={}
    for result in outcomes:
        if not isinstance(result,dict):raise ValueError("Invalid result record")
        key=(normalize(result.get("red","")),normalize(result.get("blue","")))
        if not all(key) or key in indexed:
            raise ValueError("Missing or duplicate outcome fighters")
        source=result.get("source_url","")
        if not source.startswith("https://") or " " in source:
            raise ValueError("Independently verifiable HTTPS outcome source required")
        asof=dt.datetime.fromisoformat(str(result.get("verified_at_utc","")).replace("Z","+00:00"))
        if asof.tzinfo is None or asof>verified_at:
            raise ValueError("Invalid outcome verification timestamp")
        if asof.date()<dt.date.fromisoformat(snapshot["eventDate"]):
            raise ValueError("Outcome source predates the event date")
        indexed[key]=result
    rows=[];ufc=[];lab=[];abstained=0
    for forecast in snapshot["predictions"]:
        key=normalize(forecast["red"]),normalize(forecast["blue"])
        result=indexed.pop(key,None)
        if result is None:raise ValueError("Expected bout not in independently sourced outcomes")
        outcome=str(result["outcome_red"]).upper().strip()
        if outcome not in ("0","1","DRAW","NC"):
            raise ValueError("Outcome must be 0,1,DRAW,NC")
        decided=outcome in ("0","1")
        y=int(outcome) if decided else None
        if decided:
            ufc.append((forecast["ufcashProbabilityRed"],y))
            if forecast["oddsFreeProbabilityRed"] is not None:
                lab.append((forecast["oddsFreeProbabilityRed"],y))
        else:abstained+=1
        rows.append({"red":forecast["red"],"blue":forecast["blue"],
             "result":outcome,"source":result["source_url"],
             "ufcashProbabilityRed":forecast["ufcashProbabilityRed"],
             "oddsFreeProbabilityRed":forecast["oddsFreeProbabilityRed"]})
    if indexed:raise ValueError("Unexpected additional bout outcomes")
    return {
      "schema":"JSA_PROSPECTIVE_SETTLEMENT_V1","eventDate":snapshot["eventDate"],
      "verifiedAtUTC":verified_at.isoformat(),"originalSnapshotSha256":snapshot.get("snapshotSha256"),
      "decisiveFights":len(ufc),"drawOrNC":abstained,
      "ufcash":metrics(ufc),"oddsFree":metrics(lab),
      "bouts":rows,"noROIClaim":True,"noWagersPlaced":True,
      "note":"Seven event fights are far too few to prove any strong accuracy. No verified executable bookmaker odds, so no financial ROI."
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",type=Path,required=True)
    p.add_argument("--outcomes",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    journal=json.loads(args.snapshot.read_text(encoding="utf-8"))
    with args.outcomes.open(encoding="utf-8-sig",newline="") as f:
        results=list(csv.DictReader(f))
    now=dt.datetime.now(dt.timezone.utc)
    output=reconcile(journal,results,now)
    args.output.write_text(json.dumps(output,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({k:output[k] for k in ("eventDate","decisiveFights","drawOrNC","ufcash","oddsFree")},indent=2))


if __name__=="__main__":
    main()
