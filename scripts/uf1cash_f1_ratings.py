#!/usr/bin/env python3
"""Chronological experimental F1 Elo baseline; public non-commercial Jolpica source.

This rating model IS NOT a verified betting edge or bookmaker odds provider.
No bets or wallet changes. Never train on a race on/after the as-of cutoff.
Jolpica F1: CC BY-NC-SA 4.0, noncommercial use only.
Terms: https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import math
from pathlib import Path
from urllib.request import Request,urlopen

SOURCE="https://api.jolpi.ca/ergast/f1"
SCHEMA="UF1CASH_F1_WALKFORWARD_RATINGS_V1"
K=24.0
GRID_WEIGHT=6.0
TEMP=175.0
MAX_BYTES=3_000_000
USER_AGENT="UF1Cash-Noncommercial-F1-Research/1.0"
UTC=dt.timezone.utc

def utc(value):
    if not isinstance(value,str):raise ValueError("Timestamp must be ISO text")
    t=dt.datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("Timezone required")
    return t.astimezone(UTC)

def from_payloads(payloads,cutoff):
    when=utc(cutoff)
    races=[]
    for source in payloads:
        table=source.get("MRData",{}).get("RaceTable",{})
        rows=table.get("Races",[])
        if not isinstance(rows,list):raise ValueError("Jolpica races must be a list")
        for r in rows:
            if not isinstance(r,dict):raise ValueError("Malformed race")
            if "date" not in r or "time" not in r:continue
            start=utc(r["date"]+"T"+r["time"])
            if start>=when:continue
            entrants=[]
            for result in r.get("Results",[]):
                driver=result.get("Driver",{}).get("driverId")
                position=result.get("position")
                grid=result.get("grid")
                if not isinstance(driver,str) or not driver:raise ValueError("Missing driverId")
                if not str(position).isdigit() or not str(grid).isdigit():continue
                pos=int(position);g=int(grid)
                if not (1<=pos<=30 and 0<=g<=30):raise ValueError("Race classification invalid")
                entrants.append({"id":driver,"position":pos,"grid":g})
            if len(entrants)<2:continue
            ids=[x["id"] for x in entrants];places=[x["position"] for x in entrants]
            if len(set(ids))!=len(ids) or len(set(places))!=len(places):
                raise ValueError("Duplicate driver or classification")
            winner=next((e["id"] for e in entrants if e["position"]==1),None)
            if winner is None:continue
            races.append({"start":start,"round":str(r.get("round","")),"entrants":entrants,
                          "winner":winner,"raceName":str(r.get("raceName",""))})
    races.sort(key=lambda r:(r["start"],r["round"]))
    keys=[(r["start"],r["round"]) for r in races]
    if len(set(keys))!=len(keys):raise ValueError("Duplicated F1 race across source files")
    return races

def _softmax(scores,temp=TEMP):
    if not 25<=temp<=1000:raise ValueError("Invalid temperature")
    mx=max(scores)
    exps=[math.exp((v-mx)/temp) for v in scores]
    denom=sum(exps)
    return [p/denom for p in exps]

def win_probs(entrants,ratings):
    if not isinstance(entrants,list) or len(entrants)<2:raise ValueError("Field must be complete")
    if len({x["id"] for x in entrants})!=len(entrants):raise ValueError("Duplicate driver")
    scores=[ratings.get(x["id"],1500.0)-GRID_WEIGHT*max(0,x["grid"]-1) for x in entrants]
    values=_softmax(scores)
    return {x["id"]:p for x,p in zip(entrants,values)}

def update(ratings,entrants):
    old={x["id"]:ratings.get(x["id"],1500.0) for x in entrants}
    delta={k:0.0 for k in old}
    n=len(entrants)
    for i,a in enumerate(entrants):
        for b in entrants[i+1:]:
            ra=old[a["id"]];rb=old[b["id"]]
            expected=1/(1+10**((rb-ra)/400))
            actual=1.0 if a["position"]<b["position"] else 0.0
            d=K*(actual-expected)/(n-1)
            delta[a["id"]]+=d
            delta[b["id"]]-=d
    for did in old:ratings[did]=old[did]+delta[did]
    return ratings

def evaluate(payloads,asof):
    races=from_payloads(payloads,asof)
    ratings={};results=[]
    for r in races:
        probs=win_probs(r["entrants"],ratings)
        pred=max(r["entrants"],key=lambda x:(probs[x["id"]],x["id"]))["id"]
        pole=min(r["entrants"],key=lambda x:(x["grid"] if x["grid"]>0 else 99,x["id"]))["id"]
        p=probs[r["winner"]]
        results.append({"dateUTC":r["start"].isoformat().replace("+00:00","Z"),
                        "round":r["round"],"winner":r["winner"],"predictedLeader":pred,
                        "poleDriver":pole,"modelWinnerProbability":round(p,6),
                        "correct":pred==r["winner"],"poleWon":pole==r["winner"],
                        "logLoss":-math.log(p)})
        update(ratings,r["entrants"])
    N=len(results)
    return {
      "schema":SCHEMA,"asOfUTC":utc(asof).isoformat().replace("+00:00","Z"),
      "provider":"Jolpica F1","sourceUrl":SOURCE,
      "license":"CC BY-NC-SA 4.0, non-commercial use only",
      "historicalRacesProcessed":N,
      "walkforwardTopOneAccuracy":round(sum(r["correct"] for r in results)/N,4) if N else None,
      "poleSitterWinnerBaseline":round(sum(r["poleWon"] for r in results)/N,4) if N else None,
      "walkforwardMeanMulticlassLogLoss":round(sum(r["logLoss"] for r in results)/N,4) if N else None,
      "eloRatingLeaders":[{"driverId":did,"rating":round(value,3)} for did,value in
          sorted(ratings.items(),key=lambda pair:(-pair[1],pair[0]))[:15]],
      "latestHistoricalRaceDate":results[-1]["dateUTC"] if N else None,
      "futureRaceModelProbability":None,
      "qualifyingFieldVerified":False,"oddsFeed":None,"paperBetEligible":False,
      "newPaperBets":0,"realBets":0,
      "note":"Causal historical Elo research baseline, not a calibrated forward wager. Historic starting grids are post-event archived sources; no new future field or bet inferred."
    }

def download_results(year):
    if not isinstance(year,int) or not 1950<=year<=2100:raise ValueError("Invalid season")
    url=SOURCE+"/"+str(year)+"/results.json?limit=2000"
    req=Request(url,headers={"User-Agent":USER_AGENT,"Accept":"application/json"})
    with urlopen(req,timeout=22) as response:
        buf=response.read(MAX_BYTES+1)
    if len(buf)>MAX_BYTES:raise ValueError("F1 season response too large")
    return json.loads(buf)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--years",nargs="+",type=int,required=True)
    p.add_argument("--asof",required=True)
    p.add_argument("--output",type=Path,required=True)
    opt=p.parse_args()
    years=sorted(set(opt.years))
    if len(years)>4:raise ValueError("Maximum four historical seasons per check")
    result=evaluate([download_results(year) for year in years],opt.asof)
    opt.output.parent.mkdir(parents=True,exist_ok=True)
    with opt.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False,allow_nan=False)
        f.write("\n")
    print(json.dumps({"races":result["historicalRacesProcessed"],
           "bets":result["newPaperBets"],"historicalModelAccuracy":result["walkforwardTopOneAccuracy"]}))

if __name__=="__main__":
    main()
