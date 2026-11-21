#!/usr/bin/env python3
"""Daily five-sport read-only UF1Cash fixture watch; NOT odds discovery.

Official/public calendar dates are not model forecasts, executable prices,
real bets, or authenticated fresh source observations. The watched fixtures
were captured in a separate explicitly dated source file.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlparse

SPORTS=("UFC","F1","RUGBY_UNION","HORSE_RACING","CRICKET")
TZ_SAST=dt.timezone(dt.timedelta(hours=2))

def overview(goal:dict, policy:dict, watch:dict, at:dt.datetime|None=None, f1:dict|None=None)->dict:
    now=at or dt.datetime.now(TZ_SAST)
    if now.tzinfo is None: raise ValueError("Timestamp must include timezone")
    today=now.astimezone(TZ_SAST).date()
    if goal.get("schema")!="UF1CASH_GOAL_STATUS_V1" or policy.get("schema")!="UF1CASH_LOCKED_25K_CHALLENGE_V1":
        raise ValueError("Unknown authoritative goal/policy")
    if tuple(goal.get("allowedSports",()))!=SPORTS or tuple(policy.get("allowedSports",()))!=SPORTS:
        raise ValueError("Scope must match the five authorised sports")
    if goal.get("allInAllocationPercent")!=100 or goal.get("targetBalanceZAR")!="25000.00":
        raise ValueError("All-in milestone must remain unchanged")
    if watch.get("schema")!="UF1CASH_PUBLIC_FIXTURE_WATCH_V1":
        raise ValueError("Unknown watchlist")
    observations=watch.get("fixtures")
    if not isinstance(observations,list):raise ValueError("Fixture list required")
    valid={sport:[] for sport in SPORTS}
    identifiers=set()
    for q in observations:
        if not isinstance(q,dict): raise ValueError("Invalid fixture")
        sport=q.get("sport");eid=q.get("eventId")
        if sport not in SPORTS or not isinstance(eid,str) or not eid or eid in identifiers:
            raise ValueError("Duplicate or unapproved fixture")
        identifiers.add(eid)
        name=q.get("name")
        if not isinstance(name,str) or not name.strip():
            raise ValueError("Missing fixture name")
        source=q.get("sourceUrl")
        if not isinstance(source,str):
            raise ValueError("Missing source")
        parsed=urlparse(source)
        if parsed.scheme!="https" or not parsed.hostname or not parsed.path:
            raise ValueError("Attributable HTTPS source required")
        try:day=dt.date.fromisoformat(q["date"])
        except (ValueError,TypeError,KeyError) as e:raise ValueError("Invalid date") from e
        if day>=today:
            valid[sport].append({"eventId":eid,"name":name,"eventDate":day.isoformat(),
              "sourceUrl":source,"sourceKind":q.get("kind"),"marketVerified":False,
              "modelProbabilityVerified":False,"publicQuoteVerified":False,
              "paperBetEligible":False})
    report={}
    for sport in SPORTS:
        fixtures=sorted(valid[sport],key=lambda e:(e["eventDate"],e["eventId"]))
        report[sport]={"upcomingSourceListedCount":len(fixtures),
         "modelAndQuoteEligibleCount":0,"watchStatus":"SOURCE_ONLY_NO_FROZEN_MODEL_AND_PRICE",
         "events":fixtures}
    if f1 is not None:
        if f1.get("schema")!="UFCASH_F1_SOURCE_FEED_V1":
            raise ValueError("Unknown calendar observation format")
        report["F1"]["jolpicaUpcomingRaceCount"]=sum(x.get("status")=="UPCOMING" for x in f1.get("races",[]))
        report["F1"]["jolpicaCalendarObserved"]=True
    else:
        report["F1"]["jolpicaCalendarObserved"]=False
    return {"schema":"UF1CASH_DAILY_FIVE_SPORT_READINESS_V1",
       "observedAtSAST":now.astimezone(TZ_SAST).isoformat(),
       "sourceWatchlistLastReviewedDateSAST":watch["sourceReviewedDateSAST"],
       "currency":"ZAR",
       "workingAvailableVirtualZAR":goal["availableBalanceZAR"],
       "virtualTargetZAR":"25000.00",
       "unresolvedOriginalStakeLockedZAR":goal["lockedHistoricalPendingStakeZAR"],
       "developmentFocusPercent":policy["developmentFocusPercent"],
       "sports":report,"scheduledEventsListed":sum(len(x) for x in valid.values()),
       "validatedPreEventSelections":0,"simulatedTicketsCreated":0,"realBetsPlaced":0,
       "noMarketQuoteOrPredictiveModelDataInWatchlist":True,
       "note":"Manually sourced date-only fixture watchlist: NOT current in-play odds, not an automated bookmaker search, and not a forward paper betting decision. Re-check source before freeze."}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--goal",type=Path,required=True)
    p.add_argument("--policy",type=Path,required=True)
    p.add_argument("--watchlist",type=Path,required=True)
    p.add_argument("--f1",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    load=lambda path:json.loads(path.read_text(encoding="utf-8"))
    f1=load(a.f1) if a.f1 and a.f1.is_file() else None
    result=overview(load(a.goal),load(a.policy),load(a.watchlist),f1=f1)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as out:
        json.dump(result,out,indent=2,ensure_ascii=False)
        out.write("\n")
    print(json.dumps({"futureSourceListed":result["scheduledEventsListed"],
                      "qualifiedBets":0,"currentVirtualZAR":result["workingAvailableVirtualZAR"]}))

if __name__=="__main__":main()
