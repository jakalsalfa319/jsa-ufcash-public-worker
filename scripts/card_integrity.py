#!/usr/bin/env python3
"""Official-card integrity gate for archived, precommitted UFC research.

A fighter name appearing anywhere on a UFC page is NOT a confirmed matchup.
This gate requires two fighters inside the SAME bout <li> on the official event
page, plus consistent identities in both previously frozen prediction journals.
It does not verify that a fight was completed and does not calculate betting ROI.
The source page can change; this records SHA-256 provenance for each observation.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata
from urllib.request import Request, urlopen

EVENT_DATE = "2026-11-21"
EVENT_START_UTC = dt.datetime(2026,11,21,15,0,tzinfo=dt.timezone.utc)
SOURCE_URLS = (
    "https://www.ufc.com/event/ufc-fight-night-november-21-2026",
    "https://www.ufc.com/index.php/event/ufc-fight-night-november-21-2026",
)
PAIRS = (
    ("Jiri Prochazka","Navajo Stirling"),
    ("Aljamain Sterling","Kevin Vallejos"),
    ("Dan Hooker","Brian Ortega"),
    ("Kyoji Horiguchi","Asu Almabayev"),
    ("Jared Cannonier","Ikram Aliskerov"),
    ("Aleksandre Topuria","Santiago Luna"),
    ("Shamil Gaziev","Tallison Teixeira"),
)


def canonical(value):
    raw=unicodedata.normalize("NFKD",str(value))
    return re.sub(r"[^a-z0-9]","",raw.encode("ascii","ignore").decode("ascii").lower())


class BoutParser(HTMLParser):
    """Capture each individual HTML list item, never the whole page as a bout."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._stack=[]
        self._ignore=0
        self.bouts=[]

    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):
            self._ignore+=1
        if tag=="li":
            self._stack.append([])

    def handle_data(self,data):
        if not self._ignore:
            for section in self._stack:
                section.append(data)

    def handle_endtag(self,tag):
        if tag=="li" and self._stack:
            self.bouts.append(" ".join(self._stack.pop()))
        if tag in ("script","style","noscript") and self._ignore>0:
            self._ignore-=1


def paired_bouts(html):
    parser=BoutParser()
    parser.feed(html)
    results=[]
    for a,b in PAIRS:
        key_a,key_b=canonical(a),canonical(b)
        found=[]
        for section in parser.bouts:
            flat=canonical(section)
            # A single listed bout cannot contain another tracked fighter:
            # prevents accidentally matching a navigation/list parent.
            if key_a not in flat or key_b not in flat:
                continue
            others=sum(canonical(name) in flat for pair in PAIRS
                       for name in pair if canonical(name) not in (key_a,key_b))
            if others:
                continue
            found.append(section)
        results.append({"fighterA":a,"fighterB":b,
                        "officialBoutPresent":len(found)==1,
                        "matchingSections":len(found)})
    return results


def validate_journals(classic,frontier):
    if classic.get("schema")!="JSA_EVENT_JOURNAL_V1" or classic.get("eventDate")!=EVENT_DATE or classic.get("status")!="PRE_EVENT_RESEARCH_ONLY":
        raise ValueError("Original research journal schema/event mismatch")
    if frontier.get("schema")!="JSA_FRONTIER_PROSPECTIVE_V2" or frontier.get("eventDate")!=EVENT_DATE:
        raise ValueError("Frontier research journal schema/event mismatch")
    if len(classic.get("predictions",[]))!=len(PAIRS) or len(frontier.get("predictions",[]))!=len(PAIRS):
        raise ValueError("Both frozen journals must contain exactly seven pairs")
    t1=dt.datetime.fromisoformat(classic["generatedAtUTC"].replace("Z","+00:00"))
    t2=dt.datetime.fromisoformat(frontier["recordedAtUTC"].replace("Z","+00:00"))
    if t1.utcoffset() is None or t2.utcoffset() is None or not(t1<EVENT_START_UTC and t2<EVENT_START_UTC):
        raise ValueError("Research journals must have genuine pre-event timestamps")
    for idx,(a,b) in enumerate(PAIRS):
        v1=classic["predictions"][idx];v2=frontier["predictions"][idx]
        if (canonical(v1["red"]),canonical(v1["blue"]))!=(canonical(a),canonical(b)):
            raise ValueError("Original journal changed at index "+str(idx))
        if (canonical(v2["fighterA"]),canonical(v2["fighterB"]))!=(canonical(a),canonical(b)):
            raise ValueError("Frontier journal changed at index "+str(idx))
        if v1.get("outcome") is not None or v2.get("outcome") is not None:
            raise ValueError("Original research journals must not contain later outcomes")
        if v1.get("betPlaced") is not False or v2.get("betPlaced") is not False:
            raise ValueError("Unexpected betting record in source journal")
    return True


def verify(html,classic,frontier,url,asof,raw_sha256):
    if asof.tzinfo is None or asof.utcoffset() is None:
        raise ValueError("Observation requires timezone")
    if url not in SOURCE_URLS:
        raise ValueError("Unrecognized official source URL")
    validate_journals(classic,frontier)
    if not re.search(r"Nov(?:ember)?[\s,.]*21",html,re.I):
        raise ValueError("Official page does not mention target event date")
    if "Doha" not in html or "Stirling" not in html:
        raise ValueError("Wrong event page content")
    bouts=paired_bouts(html)
    count=sum(1 for row in bouts if row["officialBoutPresent"])
    return {
      "schema":"JSA_CARD_INTEGRITY_V1",
      "eventDate":EVENT_DATE,
      "checkedAtUTC":asof.astimezone(dt.timezone.utc).isoformat(),
      "officialEventUrl":url,
      "sourceHtmlSha256":raw_sha256,
      "journalSourcePaths":[
          "public/prospective/2026-11-21.json",
          "public/prospective/2026-11-21-frontier-v2.json"
      ],
      "expected":len(PAIRS),"listedSameBoutCount":count,
      "allSevenCurrentlyListed":count==len(PAIRS),
      "eventStartedAtCheck":asof>=EVENT_START_UTC,
      "status":("LISTED_AT_SOURCE_CHECK" if count==len(PAIRS) else "REVIEW_CARD_CHANGE"),
      "bouts":bouts,
      "resultsSettled":False,
      "actualBoutsCompletedVerified":False,
      "oddsExecutableVerified":False,
      "betsPlaced":False,
      "warning":"Listed on the UFC page at retrieval time only. This is NOT proof that the bout later took place or that betting prices were executable."
    }


def fetch_page():
    problems=[]
    for url in SOURCE_URLS:
        try:
            req=Request(url,headers={
               "User-Agent":"Mozilla/5.0 (compatible; JSA-Card-Research/1.0; public source verification)",
               "Accept":"text/html","Accept-Language":"en-US,en;q=0.9"})
            with urlopen(req,timeout=20) as response:
                content=response.read(1_000_001)
                if len(content)>1_000_000:
                    raise ValueError("Unexpected official HTML length")
                raw=content.decode("utf-8","replace")
                if len(raw)<4000:
                    raise ValueError("Official source too small/incomplete")
                return url,raw,hashlib.sha256(content).hexdigest()
        except Exception as exc:
            problems.append(str(exc)[:120])
    raise RuntimeError("Official source unreachable; no card certification: "+" | ".join(problems))


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="results/card_integrity.json")
    p.add_argument("--strict",action="store_true",help="Fail if one expected bout is absent")
    a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    classic=json.loads((root/"public/prospective/2026-11-21.json").read_text(encoding="utf-8"))
    frontier=json.loads((root/"public/prospective/2026-11-21-frontier-v2.json").read_text(encoding="utf-8"))
    url,html,hash_value=fetch_page()
    result=verify(html,classic,frontier,url,dt.datetime.now(dt.timezone.utc),hash_value)
    dest=root/a.output
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"officiallyListed":result["listedSameBoutCount"],
        "target":result["expected"],"artifact":str(dest),
        "note":"Source listing ONLY; no actual results verified."}))
    if a.strict and not result["allSevenCurrentlyListed"]:
        raise SystemExit("Official card altered or insufficient evidence; no ready-status claim")


if __name__=="__main__":
    main()
