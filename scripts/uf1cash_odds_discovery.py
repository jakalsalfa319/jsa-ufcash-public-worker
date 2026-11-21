#!/usr/bin/env python3
"""The Odds API v4 read-only research intake. No bookmaker actions or wagers.

Free account key must be provisioned as repository secret UF1CASH_ODDS_API_KEY.
Do not print the key, put it in a URL, publish raw quotes, or invent sport coverage.
Free plan quota can change; hard cap per run. An unconnected key fails closed.
Official docs: https://the-odds-api.com/liveapi/guides/v4/
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import quote
from urllib.error import HTTPError,URLError

BASE="https://api.the-odds-api.com/v4"
APPROVED_SPORTS=("UFC","F1","RUGBY_UNION","HORSE_RACING","CRICKET")
HINTS={
 "UFC":("mma","ufc","mixed martial"),
 "F1":("formula 1","formula one","f1","motorsport"),
 "RUGBY_UNION":("rugby union","rugbyunion","united rugby","currie cup"),
 "HORSE_RACING":("horse racing","horseracing","horse "),
 "CRICKET":("cricket","t20","odi"),
}
MAX_RESPONSE=750000

def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z")

def map_sports(catalog):
    """Discover provider sport keys; an absent sport remains unsupported."""
    if not isinstance(catalog,list):raise ValueError("Invalid sports catalog")
    out={k:[] for k in APPROVED_SPORTS}
    for item in catalog:
        if not isinstance(item,dict):raise ValueError("Malformed catalog item")
        key=item.get("key")
        if not isinstance(key,str) or not key or len(key)>128 or not all(ch.isalnum() or ch=="_" for ch in key):
            raise ValueError("Invalid provider key")
        if item.get("active") is not True:continue
        phrase=" ".join(str(item.get(k,"")) for k in ("key","title","description","group")).lower()
        for sport,hints in HINTS.items():
            if any(w in phrase for w in hints):
                out[sport].append({"providerKey":key,"hasOutrights":item.get("has_outrights") is True})
    return out

def get_api_json(relative_path,key,params=None):
    """Protect key in request HEADER and cap response bytes."""
    if not isinstance(key,str) or not 8<=len(key)<=500:raise ValueError("Provider key missing")
    if not isinstance(relative_path,str) or not relative_path.startswith("/") or "?" in relative_path or ".." in relative_path:
        raise ValueError("Invalid endpoint path")
    query=""
    if params:
        query="?"+"&".join(quote(str(k),safe="")+"="+quote(str(v),safe="") for k,v in params.items())
    req=Request(BASE+relative_path+query,headers={"x-api-key":key,"Accept":"application/json","User-Agent":"UF1CashResearch/1.0"})
    with urlopen(req,timeout=15) as response:
        content=response.read(MAX_RESPONSE+1)
        if len(content)>MAX_RESPONSE:raise ValueError("Provider response too large")
        return json.loads(content.decode("utf-8")),dict(response.headers)

def normalize_events(sport_key,market,payload,observed_at):
    """Only event/market coverage metadata. Never emit bookmaker prices publicly."""
    if not isinstance(payload,list):raise ValueError("Expected provider event list")
    result=[]
    for event in payload:
        if not isinstance(event,dict):raise ValueError("Invalid event")
        when=event.get("commence_time")
        if not isinstance(when,str):raise ValueError("Event missing scheduled kickoff")
        starts=dt.datetime.fromisoformat(when.replace("Z","+00:00"))
        if starts.tzinfo is None:raise ValueError("Timezone missing")
        ref=event.get("id")
        if not isinstance(ref,str) or not ref:raise ValueError("Event missing provider id")
        books=event.get("bookmakers",[])
        if not isinstance(books,list):raise ValueError("Bookmaker list invalid")
        valid_books=0;latest=[]
        for b in books:
            if not isinstance(b,dict):raise ValueError("Invalid bookmaker")
            for m in b.get("markets",[]):
                if m.get("key") != market:continue
                last=m.get("last_update")
                if not last or not isinstance(m.get("outcomes"),list):continue
                ts=dt.datetime.fromisoformat(last.replace("Z","+00:00"))
                if ts.tzinfo is None or ts>dt.datetime.fromisoformat(observed_at.replace("Z","+00:00")):
                    raise ValueError("Market time inconsistent")
                valid_books+=1
                latest.append(ts)
        result.append({
          "providerEventId":ref,"sportKey":sport_key,
          "eventStartsUTC":starts.astimezone(dt.timezone.utc).isoformat().replace("+00:00","Z"),
          "marketKey":market,"sourceBookmakerMarketCount":valid_books,
          "latestMarketObservationUTC":max(latest).isoformat().replace("+00:00","Z") if latest else None,
          "hasPriceObservation":bool(latest),
          "modelProbabilityAttached":False,"qualifiedForVirtualWager":False,
        })
    return result

def inspect(key=None,max_requests=0,clock=None):
    observed=clock or now_utc()
    if not key:
        return {"schema":"UF1CASH_ODDS_DISCOVERY_V1","status":"NOT_CONNECTED_KEY_REQUIRED",
          "observedAtUTC":observed,"source":"The Odds API v4",
          "sports":{s:[] for s in APPROVED_SPORTS},"providerRequestsCharged":0,
          "events":[],"eligibleSelections":0,"simulatedWagers":0,"realBets":0,
          "note":"Set UF1CASH_ODDS_API_KEY in private GitHub Actions secrets after creating a free provider account."}
    catalog,_=get_api_json("/sports/",key)
    found=map_sports(catalog)
    if max_requests<0 or max_requests>5:raise ValueError("Maximum of 5 charged calls/run")
    events=[];attempted=0;errors=[]
    for sport in APPROVED_SPORTS:
        for mapping in found[sport]:
            if attempted>=max_requests:break
            market="outrights" if mapping["hasOutrights"] else "h2h"
            attempted+=1
            path="/sports/"+mapping["providerKey"]+"/odds/"
            try:
                data,_=get_api_json(path,key,{"regions":"uk","markets":market,"oddsFormat":"decimal"})
                events.extend(normalize_events(mapping["providerKey"],market,data,observed))
            except (HTTPError,URLError,TimeoutError,ValueError) as exc:
                errors.append({"providerSportKey":mapping["providerKey"],"kind":type(exc).__name__})
    return {"schema":"UF1CASH_ODDS_DISCOVERY_V1","status":"CONNECTED_METADATA_ONLY" if not errors else "PARTIAL_SOURCE_FAILURE",
        "observedAtUTC":observed,"source":"The Odds API v4",
        "sports":found,"providerRequestsChargedUpperBound":attempted,
        "events":events,"errors":errors,"eligibleSelections":0,"simulatedWagers":0,"realBets":0,
        "note":"Provider coverage only. No raw prices redistributed; no model probabilities or authenticated executable quotes. No betting orders."}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--max-requests",type=int,default=0)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=inspect(os.getenv("UF1CASH_ODDS_API_KEY"),args.max_requests)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"status":result["status"],"events":len(result["events"]),"bets":0}))

if __name__=="__main__":main()
