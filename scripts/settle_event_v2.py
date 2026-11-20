#!/usr/bin/env python3
"""Settle BOTH frozen J$A MMA research journals without rewriting either.

Only completed, decisive bouts are scored. Draws, NC, cancelled, replaced,
postponed and unknown matchups are all reported but not counted as wins/losses.

The CSV provides a link and claimed outcome, not independent proof of its
contents. Any source-content audit must happen separately before publishing
a "verified" result. No bets, prices or profit calculations are made.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path
from urllib.parse import urlparse

from scripts.card_integrity import PAIRS,EVENT_DATE,EVENT_START_UTC,canonical,validate_journals
from scripts.prospective_journal import digest

KNOWN_STATUSES = frozenset((
    "COMPLETED","DRAW","NO_CONTEST","CANCELLED",
    "REPLACED","POSTPONED","PENDING"
))
NO_SCORE = KNOWN_STATUSES-{"COMPLETED"}
SOURCES = frozenset(("ufc.com","www.ufc.com","ufcstats.com","www.ufcstats.com",
                     "ufc.ru","www.ufc.ru","ufcespanol.com","us.ufcespanol.com"))


def wilson_lower(w,n):
    if not n:return None
    z=1.959963984540054
    p=w/n
    den=1+z*z/n
    return max(0.,(p+z*z/(2*n)-z*math.sqrt((p*(1-p)+z*z/(4*n))/n))/den)


def score(points):
    n=len(points)
    if not n:
        return {"eligible":0,"correct":0,"accuracy":None,"brier":None,
                "logLoss":None,"wilson95Lower":None}
    wins=sum(int((p>=.5)==bool(y)) for p,y in points)
    return {
        "eligible":n,"correct":wins,"accuracy":wins/n,
        "brier":sum((p-y)**2 for p,y in points)/n,
        "logLoss":-sum(y*math.log(max(1e-12,p))+
                       (1-y)*math.log(max(1e-12,1-p)) for p,y in points)/n,
        "wilson95Lower":wilson_lower(wins,n)
    }


def as_utc(raw):
    t=dt.datetime.fromisoformat(str(raw).replace("Z","+00:00"))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("Evidence timestamp needs UTC offset")
    return t.astimezone(dt.timezone.utc)


def accepted_source(url):
    u=urlparse(url)
    return u.scheme=="https" and u.hostname in SOURCES and bool(u.path)


def pair_key(a,b):
    x,y=canonical(a),canonical(b)
    if not x or not y or x==y:
        raise ValueError("Invalid opponent pair")
    return tuple(sorted((x,y)))


def reconcile(original,frontier,inputs,now):
    validate_journals(original,frontier)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Settlement time must carry timezone")
    if now.astimezone(dt.timezone.utc)<EVENT_START_UTC:
        raise ValueError("Cannot reconcile outcomes before event starts")
    key_to_i={pair_key(a,b):i for i,(a,b) in enumerate(PAIRS)}
    outcome={}
    for r in inputs:
        key=pair_key(r.get("fighterA",""),r.get("fighterB",""))
        if key not in key_to_i or key in outcome:
            raise ValueError("Duplicate, mismatched or unexpected bout in results")
        status=str(r.get("status","")).upper().strip()
        if status not in KNOWN_STATUSES:
            raise ValueError("Unrecognized bout status "+status)
        winner=str(r.get("winner","")).strip()
        source=str(r.get("source_url","")).strip()
        checked=str(r.get("verified_at_utc","")).strip()
        if status=="PENDING":
            if winner or source or checked:
                raise ValueError("PENDING cannot claim a winner or verified source")
        else:
            if not accepted_source(source) or not checked:
                raise ValueError("Non-pending result needs UFC-hosted reference URL and timestamp")
            observed=as_utc(checked)
            if observed>now.astimezone(dt.timezone.utc):
                raise ValueError("Evidence timestamp is later than reconciliation")
            if status in ("COMPLETED","DRAW","NO_CONTEST") and observed<EVENT_START_UTC:
                raise ValueError("Fight result timestamp precedes event")
        a,b=PAIRS[key_to_i[key]]
        if status=="COMPLETED":
            if canonical(winner) not in (canonical(a),canonical(b)):
                raise ValueError("Completed fight must name an actual winning fighter")
        elif winner:
            raise ValueError("Non-decisive or cancelled bout cannot have a winner")
        outcome[key]={"status":status,"winner":winner,"source":source,
                      "verifiedAt":checked}
    metrics={"ufcash":[],"oddsFree":[],"frontier":[],"frontierSelected":[]}
    rows=[]
    statuses={}
    for i,(a,b) in enumerate(PAIRS):
        key=pair_key(a,b)
        ev=outcome.get(key,{"status":"PENDING","winner":"","source":"","verifiedAt":""})
        status=ev["status"]
        statuses[status]=statuses.get(status,0)+1
        a_p=original["predictions"][i]
        b_p=frontier["predictions"][i]
        scored=status=="COMPLETED"
        resultA=int(canonical(ev["winner"])==canonical(a)) if scored else None
        if scored:
            metrics["ufcash"].append((float(a_p["ufcashProbabilityRed"]),resultA))
            q=a_p.get("oddsFreeProbabilityRed")
            if q is not None:metrics["oddsFree"].append((float(q),resultA))
            z=b_p.get("redProbability")
            if z is not None:
                metrics["frontier"].append((float(z),resultA))
                if b_p.get("passesValidationLockedGate") is True:
                    metrics["frontierSelected"].append((float(z),resultA))
        rows.append({
            "fighterA":a,"fighterB":b,"status":status,
            "winner":ev["winner"] or None,
            "resultA":resultA,"scored":scored,
            "sourceUrl":ev["source"] or None,
            "sourceContentsIndependentlyChecked":False
        })
    completed=statuses.get("COMPLETED",0)
    return {
      "schema":"JSA_MULTI_MODEL_RECONCILIATION_V1",
      "eventDate":EVENT_DATE,"reconciledAtUTC":now.astimezone(dt.timezone.utc).isoformat(),
      "sourceJournalsUnchanged":True,
      "originalSourceSha256":original.get("snapshotSha256"),
      "frontierRunSha256":frontier.get("sourceReportSha256"),
      "status":("NO_SCORED_BOUTS" if completed==0 else
                "RECONCILED_UNVERIFIED_EVIDENCE" if completed<7 else
                "COMPLETE_RECONCILIATION_UNVERIFIED_EVIDENCE"),
      "expected":len(PAIRS),"decisiveScored":completed,
      "statusCounts":statuses,"modelCoverage":{
        name:len(values) for name,values in metrics.items()
      },
      "scores":{name:score(values) for name,values in metrics.items()},
      "bouts":rows,
      "sourceContentVerification":"URLs and timestamps are supplied; underlying page assertions NOT yet audited by this function.",
      "financialROI":None,"automatedBets":False,"accuracy99_9Verified":False,
      "warning":"Do not call this independently verified until outcome text is compared against an authentic UFC result source; excludes cancelled/replaced/missing bouts."
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--outcomes",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    a=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    original=json.loads((root/"public/prospective/2026-11-21.json").read_text(encoding="utf-8"))
    frontier=json.loads((root/"public/prospective/2026-11-21-frontier-v2.json").read_text(encoding="utf-8"))
    with a.outcomes.open(encoding="utf-8-sig",newline="") as f:
        data=list(csv.DictReader(f))
    report=reconcile(original,frontier,data,dt.datetime.now(dt.timezone.utc))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["status"],"decisiveScored":report["decisiveScored"],
        "statusCounts":report["statusCounts"],
        "modelAccuracy":{k:v["accuracy"] for k,v in report["scores"].items()},
        "sourceContentsVerified":False},indent=2))


if __name__=="__main__":
    main()
