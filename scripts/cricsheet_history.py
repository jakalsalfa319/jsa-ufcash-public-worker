#!/usr/bin/env python3
"""Historical Cricsheet T20 match parser with strict training cutoff.

Data source https://cricsheet.org/matches/ ; ODC-BY 1.0, attribution required.
NO live feed, bookmaker data, forecasts or paper bets.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path

SOURCE = "https://cricsheet.org/matches/"
ATTRIBUTION = "Cricsheet.org (ODC-BY 1.0)"

def history_row(data: dict, training_cutoff: str) -> dict:
    if not isinstance(data, dict) or not isinstance(data.get("info"), dict):
        raise ValueError("Invalid Cricsheet data")
    info = data["info"]
    if info.get("match_type") not in ("T20", "T20I"):
        raise ValueError("Only T20/T20I history supported")
    teams = info.get("teams")
    if not isinstance(teams, list) or len(teams) != 2 or not all(isinstance(x,str) and x.strip() for x in teams):
        raise ValueError("Exactly two team names required")
    if teams[0].casefold() == teams[1].casefold():
        raise ValueError("Same team twice")
    dates = info.get("dates")
    if not isinstance(dates,list) or not dates:
        raise ValueError("Missing match dates")
    try:
        match_date = dt.date.fromisoformat(dates[0])
        cutoff = dt.date.fromisoformat(training_cutoff)
    except (TypeError,ValueError) as e:
        raise ValueError("Invalid dates") from e
    if match_date >= cutoff:
        raise ValueError("LOOKAHEAD_BLOCKED: match is not before training cutoff")
    outcome = info.get("outcome")
    if not isinstance(outcome,dict):
        raise ValueError("No outcome record")
    winner = outcome.get("winner")
    if winner is not None and winner not in teams:
        raise ValueError("Winner not among the teams")
    return {
        "schema":"UF1CASH_CRICSHEET_HISTORICAL_ROW_V1",
        "matchDate":match_date.isoformat(),"trainingCutoff":cutoff.isoformat(),
        "format":info["match_type"],"teamA":teams[0],"teamB":teams[1],
        "historicalWinner":winner,"resultType":"DECISIVE" if winner else "NON_DECISIVE",
        "sourceUrl":SOURCE,"requiredAttribution":ATTRIBUTION,
        "modelProbability":None,"odds":None,"qualifyingForwardBet":False
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--cutoff",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=history_row(json.loads(args.input.read_text(encoding="utf-8")),args.cutoff)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as dest:
        json.dump(result,dest,indent=2,ensure_ascii=False)
        dest.write("\n")
    print(json.dumps({"result":result["resultType"],"betCreated":False}))

if __name__=="__main__":
    main()
