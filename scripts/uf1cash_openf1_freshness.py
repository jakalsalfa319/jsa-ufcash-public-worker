#!/usr/bin/env python3
"""Independent F1 completed-race freshness check, OpenF1 historical free API.

No betting odds, forward race forecasts, or virtual bets. Historical data
only, minimum 30 min after session end. Source intended for personal,
noncommercial research: https://openf1.org/
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen

BASE="https://api.openf1.org/v1"
SCHEMA="UF1CASH_OPENF1_FRESHNESS_V1"
MAX_BYTES=1100000
UTC=dt.timezone.utc

def moment(value):
    if not isinstance(value,str):raise ValueError("Timestamp missing")
    x=dt.datetime.fromisoformat(value.replace("Z","+00:00"))
    if x.tzinfo is None:raise ValueError("Timezone required")
    return x.astimezone(UTC)

def historical_race(sessions,at):
    now=moment(at)
    if not isinstance(sessions,list):raise ValueError("OpenF1 sessions response invalid")
    possible=[]
    for row in sessions:
        if not isinstance(row,dict):raise ValueError("Malformed OpenF1 session")
        if row.get("session_type")!="Race" or row.get("is_cancelled") is True:continue
        if row.get("date_end") is None:continue
        end=moment(row["date_end"])
        if end+dt.timedelta(minutes=30)>now:continue
        key=row.get("session_key")
        if isinstance(key,bool) or not isinstance(key,int) or key<=0:
            raise ValueError("OpenF1 session key malformed")
        possible.append((end,key,row))
    if not possible:return None
    return sorted(possible,key=lambda x:(-x[0].timestamp(),x[1]))[0][2]

def results_summary(data,session,at):
    if not isinstance(data,list):raise ValueError("Session result array invalid")
    if not isinstance(session,dict):raise ValueError("Missing source session")
    participants=[];positions=set();numbers=set()
    for row in data:
        if not isinstance(row,dict):raise ValueError("Bad result row")
        if row.get("session_key")!=session["session_key"]:
            raise ValueError("Wrong results for session")
        pos=row.get("position")
        number=row.get("driver_number")
        if isinstance(pos,bool) or not isinstance(pos,int) or pos<1 or pos>40:continue
        if isinstance(number,bool) or not isinstance(number,int) or number<1 or number>99:continue
        if pos in positions or number in numbers:
            raise ValueError("Duplicated result position or driver")
        positions.add(pos);numbers.add(number)
        participants.append({"position":pos,"driverNumber":number,
          "dnf":row.get("dnf") is True,"dns":row.get("dns") is True,"dsq":row.get("dsq") is True})
    participants.sort(key=lambda x:x["position"])
    if len(participants)<10 or 1 not in positions:
        raise ValueError("Insufficient official-style completed-race result detail")
    winner=participants[0]
    if winner["dnf"] or winner["dns"] or winner["dsq"]:
        raise ValueError("Invalid race winner status")
    end=moment(session["date_end"])
    now=moment(at)
    lag=(now-end).total_seconds()/86400
    return {"schema":SCHEMA,
       "observedAtUTC":now.isoformat().replace("+00:00","Z"),
       "source":"OpenF1 historical session results",
       "sourceUrl":BASE+"/sessions",
       "sourceSessionKey":session["session_key"],
       "sourceSessionResultsUrl":BASE+"/session_result?session_key="+str(session["session_key"]),
       "latestCompletedRaceEndUTC":end.isoformat().replace("+00:00","Z"),
       "latestCompletedRaceName":session.get("session_name","Race"),
       "latestCompletedRaceLocation":session.get("location"),
       "daysSinceLatestCompletedRace":round(lag,2),
       "freshnessStatus":"RECENT_WITHIN_30_DAYS" if lag<=30 else "STALE_OVER_30_DAYS",
       "classifications":len(participants),
       "reportedWinnerDriverNumber":winner["driverNumber"],
       "independentlyCrossCheckedWithOfficialF1":False,
       "qualifyingAndPreEventFeatureGridPresent":False,
       "forecastProbability":None,"bettableOdds":None,
       "paperBetEligible":False,"virtualBets":0,"realBets":0,
       "note":"Historical data source check only; OpenF1 independent of F1/FIA; terms personal and noncommercial. Do not treat historical outcomes as prospective race forecasts."}

def fetch_json(path,params):
    if path not in ("/sessions","/session_result"):
        raise ValueError("Only documented read-only OpenF1 endpoints allowed")
    uri=BASE+path+"?"+urlencode(params)
    req=Request(uri,headers={"User-Agent":"UF1Cash-Noncommercial-Historical-Audit/1.0","Accept":"application/json"})
    with urlopen(req,timeout=18) as r:
        buf=r.read(MAX_BYTES+1)
    if len(buf)>MAX_BYTES:raise ValueError("OpenF1 response too large")
    return json.loads(buf)

def inspect(year,asof=None):
    if isinstance(year,bool) or not isinstance(year,int) or not 2023<=year<=2100:
        raise ValueError("OpenF1 history is available from 2023 onward")
    now=asof or dt.datetime.now(UTC).isoformat().replace("+00:00","Z")
    sessions=fetch_json("/sessions",{"year":year,"session_type":"Race"})
    found=historical_race(sessions,now)
    if found is None:
        return {"schema":SCHEMA,"observedAtUTC":now,"source":"OpenF1",
           "freshnessStatus":"NO_COMPLETED_RACE","paperBetEligible":False,
           "forecastProbability":None,"virtualBets":0,"realBets":0}
    data=fetch_json("/session_result",{"session_key":found["session_key"]})
    return results_summary(data,found,now)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--year",required=True,type=int)
    p.add_argument("--output",required=True,type=Path)
    opts=p.parse_args()
    result=inspect(opts.year)
    opts.output.parent.mkdir(parents=True,exist_ok=True)
    with opts.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"status":result["freshnessStatus"],
        "latestRace":result.get("latestCompletedRaceEndUTC"),
        "virtualBets":0,"realBets":0}))

if __name__=="__main__":
    main()
