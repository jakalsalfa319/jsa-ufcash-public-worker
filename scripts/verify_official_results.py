#!/usr/bin/env python3
"""Read-only UFCStats result verification and frozen-model score preparation.

The official UFCStats completed-event index identifies the event. Individual
fight-details pages must prove BOTH fighter names and the W/L, D/D, or NC/NC
status before any frozen prediction is scored. Missing, replaced, or disputed
matches remain PENDING. No sportsbook, financial data or credentials.

This is NOT an automatic published settlement; output is an immutable-by-job
GitHub Actions artifact for independent review. Any source failure is visible.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from bs4 import BeautifulSoup

from scripts.card_integrity import PAIRS,EVENT_START_UTC,canonical
from scripts.settle_event_v2 import reconcile

INDEX="http://ufcstats.com/statistics/events/completed?page=all"
HTTPS_INDEX="https://ufcstats.com/statistics/events/completed?page=all"
MAX_BYTES=2_000_000


def safe_url(url, allowed_path):
    p=urlparse(url)
    if p.scheme not in ("https","http") or p.hostname not in ("ufcstats.com","www.ufcstats.com"):
        raise ValueError("Outside UFCStats official domain")
    if not p.path.startswith(allowed_path) or p.username or p.password:
        raise ValueError("Unexpected UFCStats URL path")
    return url


def get_source(url, path):
    safe_url(url,path)
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; JSA-Research-Result-Audit/1.0)","Accept":"text/html"})
    with urlopen(req,timeout=18) as res:
        safe_url(res.geturl(),path)
        blob=res.read(MAX_BYTES+1)
    if len(blob)>MAX_BYTES or len(blob)<300:
        raise ValueError("UFCStats source too large/small")
    return blob.decode("utf-8","replace"),hashlib.sha256(blob).hexdigest()


def find_event_link(index_html):
    """Exact event name AND target date, not the latest event index row."""
    soup=BeautifulSoup(index_html,"html.parser")
    hits=[]
    for row in soup.select("tr.b-statistics__table-row"):
        a=row.select_one('a[href*="/event-details/"]')
        if not a:continue
        name=a.get_text(" ",strip=True)
        text=row.get_text(" ",strip=True).lower()
        n=canonical(name)
        if "prochazka" in n and "stirling" in n and ("november 21, 2026" in text or "nov. 21, 2026" in text or "nov 21, 2026" in text):
            hits.append(safe_url(a.get("href",""),"/event-details/"))
    if len(hits)!=1:
        return None
    return hits[0]


def parse_event_fights(html):
    soup=BeautifulSoup(html,"html.parser")
    headline=soup.select_one(".b-content__title-highlight")
    head=headline.get_text(" ",strip=True) if headline else ""
    if "prochazka" not in canonical(head) or "stirling" not in canonical(head):
        raise ValueError("UFCStats event identity mismatch")
    meta=soup.get_text(" ",strip=True)
    if "Nov. 21, 2026" not in meta and "November 21, 2026" not in meta:
        raise ValueError("Event date not confirmed by UFCStats")
    rows=[]
    for tr in soup.select("tr.b-fight-details__table-row[data-link]"):
        link=safe_url(tr.get("data-link",""),"/fight-details/")
        tds=tr.find_all("td",recursive=False)
        if len(tds)<2:continue
        # The UFCStats table keeps both fighter names in the second cell.
        names=[]
        for a in tds[1].find_all("a"):
            name=a.get_text(" ",strip=True)
            if name and canonical(name) not in [canonical(x) for x in names]:
                names.append(name)
        if len(names)==2:
            rows.append({"fighters":names,"fightUrl":link})
    return rows


def parse_fight_details(html):
    soup=BeautifulSoup(html,"html.parser")
    actors=soup.select(".b-fight-details__person")
    if len(actors)!=2:
        raise ValueError("Official fight page must identify exactly two athletes")
    people=[]
    for node in actors:
        name=node.select_one(".b-fight-details__person-name")
        status=node.select_one(".b-fight-details__person-status")
        if name is None or status is None:
            raise ValueError("Incomplete UFCStats official result elements")
        name=name.get_text(" ",strip=True)
        code=status.get_text(" ",strip=True).upper()
        people.append({"name":name,"status":code})
    a,b=people
    pair={a["status"],b["status"]}
    if (a["status"],b["status"])==("W","L"):return a["name"],"COMPLETED",people
    if (a["status"],b["status"])==("L","W"):return b["name"],"COMPLETED",people
    if a["status"]==b["status"]=="D":return "","DRAW",people
    if a["status"]==b["status"]=="NC":return "","NO_CONTEST",people
    raise ValueError("Unresolved UFCStats outcome status "+repr(pair))


def match_exact(a,b):
    left={canonical(a),canonical(b)}
    return len(left)==2


def collect(index_html,event_html,details,observed,source_map):
    """Pure function for fixture-driven tests and production observations."""
    link=find_event_link(index_html)
    if not link:raise ValueError("Exact completed UFC event not found")
    event=parse_event_fights(event_html)
    outcome=[]
    for a,b in PAIRS:
        expected={canonical(a),canonical(b)}
        matches=[r for r in event if {canonical(x) for x in r["fighters"]}==expected]
        if len(matches)!=1:continue
        row=matches[0]
        body=details.get(row["fightUrl"])
        if not body:continue
        try:
            winner,status,found=parse_fight_details(body)
            got={canonical(person["name"]) for person in found}
            if got!=expected:continue
            outcome.append({
                "fighterA":a,"fighterB":b,"status":status,"winner":winner,
                "source_url":row["fightUrl"],
                "verified_at_utc":observed.isoformat()
            })
        except ValueError:
            continue
    return outcome


def verify_real_sources(now,root):
    from scripts.card_integrity import validate_journals
    first=json.loads((root/"public/prospective/2026-11-21.json").read_text())
    newer=json.loads((root/"public/prospective/2026-11-21-frontier-v2.json").read_text())
    validate_journals(first,newer)
    if now<EVENT_START_UTC:
        raise ValueError("Event has not started; no results can be verified yet")
    observations={}
    try:
        index,hash_idx=get_source(HTTPS_INDEX,"/statistics/events/completed")
        observations["completedIndexSha256"]=hash_idx
        event_url=find_event_link(index)
        if not event_url:raise RuntimeError("Event missing from completed index")
        event_html,event_hash=get_source(event_url,"/event-details/")
        observations.update({"eventUrl":event_url,"eventHtmlSha256":event_hash})
        entries=parse_event_fights(event_html)
        data={};source_proofs={}
        # Only download event's exact seven tracked bouts, avoiding unrelated rows.
        wanted={frozenset(canonical(x) for x in pair) for pair in PAIRS}
        for row in entries:
            if frozenset(canonical(x) for x in row["fighters"]) not in wanted:
                continue
            url=row["fightUrl"]
            if url in data:continue
            try:
                html,sha=get_source(url,"/fight-details/")
                data[url]=html
                source_proofs[url]=sha
            except Exception as e:
                observations.setdefault("unavailableFightUrls",[]).append({
                    "url":url,"reason":str(e)[:120]
                })
        completed=collect(index,event_html,data,now,source_proofs)
        observations["fightSourceSha256"]=source_proofs
    except Exception as exc:
        # Visible failure: never claim verified outcomes from inaccessible data.
        completed=[]
        observations["sourceFailure"]=str(exc)[:320]
    report=reconcile(first,newer,completed,now)
    validated={frozenset((canonical(r["fighterA"]),canonical(r["fighterB"]))):r
               for r in completed}
    for row in report["bouts"]:
        key=frozenset((canonical(row["fighterA"]),canonical(row["fighterB"])))
        if key in validated:
            row["sourceContentsIndependentlyChecked"]=True
            row["evidencePage"]=validated[key]["source_url"]
            row["evidenceSha256"]=observations.get("fightSourceSha256",{}).get(row["evidencePage"])
    verifiable=sum(1 for r in report["bouts"] if r["sourceContentsIndependentlyChecked"])
    report["sourceContentVerification"]="Parsed official UFCStats result statuses and exactly-matched fighters for "+str(verifiable)+" bouts; other bouts still PENDING"
    report["status"]=("OFFICIAL_RESULTS_VERIFIED" if verifiable==7 else
                      "PARTIAL_OFFICIAL_RESULTS" if verifiable else
                      "AWAITING_OFFICIAL_RESULTS")
    report["verifiedDecisiveBouts"]=sum(r["scored"] and r["sourceContentsIndependentlyChecked"] for r in report["bouts"])
    report["automaticPublicationApproved"]=False
    return {"schema":"JSA_UFCSTATS_SOURCE_AUDIT_V1","createdUTC":now.isoformat(),
            "source":"Official UFCStats completed-fight and individual fight-details pages",
            "observations":observations,"result":report,
            "publishedFinalAccuracy":False,
            "warning":"Artifact-only independent evidence audit; do not publish definitive return/99.9% claims from seven fights."}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="results/official_outcomes_audit.json")
    args=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    now=dt.datetime.now(dt.timezone.utc)
    if now<EVENT_START_UTC:
        raise SystemExit("Scheduled post-event audit cannot run before event start")
    obj=verify_real_sources(now,root)
    path=root/args.output
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    s=obj["result"]
    print(json.dumps({"status":s["status"],"verifiedDecisiveBouts":s["verifiedDecisiveBouts"],
      "count":s["decisiveScored"],"sourceError":obj["observations"].get("sourceFailure"),
      "artifact":str(path),"noAutomaticPublication":True}))
    print("NOTE: This script never changes original forecast files.")


if __name__=="__main__":
    main()
