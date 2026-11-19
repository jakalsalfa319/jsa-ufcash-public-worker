#!/usr/bin/env python3
"""Clean-room Elo challenger on UFCash's *already downloaded* UFCStats mirror.

Inspired by the standard Elo formula, not copied from NBAtrev/UFC-Elo-Engine.
Only completed decisive fights BEFORE the upcoming event can change ratings.
All results on the same date are scored before any that day's results are applied.
This is NOT an odds-driven model or evidence of a profitable betting edge.
"""
import datetime as dt
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


class Elo:
    def __init__(self, k=24, scale=400):
        self.k = k
        self.scale = scale
        self.rating = defaultdict(lambda: 1500.0)
        self.count = defaultdict(int)

    def prob(self, a, b):
        return 1.0 / (1.0 + 10.0 ** ((self.rating[b] - self.rating[a]) / self.scale))

    def rate_day(self, records):
        """All records use pre-day ratings, avoiding same-day information leakage."""
        changes = defaultdict(float)
        increments = defaultdict(int)
        observed = []
        for item in records:
            a, b, winner = item["a"], item["b"], item["winner"]
            if a == b or winner not in (0, 1):
                raise ValueError("Invalid fight record")
            p = self.prob(a, b)
            observed.append((item, p, self.count[a], self.count[b]))
            delta = self.k * (winner - p)
            changes[a] += delta
            changes[b] -= delta
            increments[a] += 1
            increments[b] += 1
        for key, delta in changes.items():
            self.rating[key] += delta
            self.count[key] += increments[key]
        return observed


def build_history(rows, event_date, holdout_date="2024-01-01"):
    cutoff = dt.date.fromisoformat(event_date)
    holdout = dt.date.fromisoformat(holdout_date)
    filtered, seen = [], set()
    for r in rows:
        when = dt.date.fromisoformat(str(r["date"])[:10])
        if when >= cutoff:
            continue
        fight_id = str(r["fight_id"])
        if fight_id in seen:
            raise ValueError("Duplicate fight id: " + fight_id)
        seen.add(fight_id)
        a, b = str(r["r_id"]), str(r["b_id"])
        winner = int(r["winner"])
        if not a or not b or a == b or winner not in (0, 1):
            continue
        filtered.append({"date":when,"id":fight_id,"a":a,"b":b,"winner":winner})
    filtered.sort(key=lambda x: (x["date"], x["id"]))
    engine = Elo()
    evaluated = []
    i = 0
    while i < len(filtered):
        day = filtered[i]["date"]
        j = i + 1
        while j < len(filtered) and filtered[j]["date"] == day:
            j += 1
        records = engine.rate_day(filtered[i:j])
        for fight, p, count_a, count_b in records:
            if day >= holdout and count_a >= 3 and count_b >= 3:
                evaluated.append((p, fight["winner"]))
        i = j
    correct = sum(int((p >= 0.5) == bool(y)) for p, y in evaluated)
    brier = sum((p-y)**2 for p, y in evaluated)/len(evaluated) if evaluated else None
    return engine, {
        "eligible": len(evaluated), "correct": correct,
        "accuracy": correct/len(evaluated) if evaluated else None,
        "brier": brier, "holdoutStart": holdout_date,
        "fightResultsBeforeEvent": len(filtered),
        "trainingMethod": "online Elo: only earlier completed outcomes; same-day batch updates",
    }


def main():
    # Already built by UFCash setup (its input CSV and fighter IDs are publicly sourced).
    import pandas as pd
    root=Path(__file__).resolve().parents[1]
    data = root / "ufcash" / "data" / "processed" / "fights.parquet"
    if not data.is_file():
        raise SystemExit("Missing UFCash processed fights; run upstream setup first")
    upcoming = pd.read_csv(root/"card"/"upcoming.csv")
    dates = {str(x)[:10] for x in upcoming.date}
    if len(dates) != 1:
        raise SystemExit("Refusing mixed or missing event dates")
    event_date = next(iter(dates))
    fights = pd.read_parquet(data)
    cols = ["fight_id","date","r_id","b_id","winner"]
    history = fights.loc[:,cols].to_dict(orient="records")
    engine, metrics = build_history(history, event_date)
    upcoming_rows = fights[fights["outcome"] == "UPCOMING"].sort_values("card_pos")
    expected_count = len(upcoming)
    if len(upcoming_rows) != expected_count or expected_count != 7:
        raise SystemExit("Expected exactly seven verified upcoming bouts")
    results=[]
    for r in upcoming_rows.itertuples(index=False):
        rid,bid = str(r.r_id),str(r.b_id)
        count_a,count_b = engine.count[rid],engine.count[bid]
        covered = count_a>=3 and count_b>=3 and not rid.startswith("name:") and not bid.startswith("name:")
        results.append({
            "fighterA":str(r.r_name),"fighterB":str(r.b_name),
            "ufcPriorFightsA":count_a,"ufcPriorFightsB":count_b,
            "eloProbabilityA":round(engine.prob(rid,bid),6) if covered else None,
            "coverage":"COMPARABLE" if covered else "INSUFFICIENT HISTORY",
            "source":"independent chronology-safe clean-room Elo; UFCash processed fights"
        })
    out={"schema":"JSA_ELO_CHALLENGER_V1","eventDate":event_date,"k":engine.k,
         "scale":engine.scale,"metrics":metrics,"predictions":results,
         "note":"Different historical cohort from UFCash published audit. No claim of betting profitability or calibration."}
    dest=root/"results"/"elo_challenger.json"
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({"eligible":metrics["eligible"],"accuracy":metrics["accuracy"],
                      "coveredUpcoming":sum(x["coverage"]=="COMPARABLE" for x in results)}))


if __name__=="__main__":
    main()
