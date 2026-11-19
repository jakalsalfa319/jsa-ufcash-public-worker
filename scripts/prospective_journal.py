#!/usr/bin/env python3
"""Immutable-by-convention pre-event research snapshot for GitHub Actions artifact.

This script does NOT record or place bets. It refuses to label a prediction
"prospective" after the event date begins in UTC. The resulting artifact is
timestamped by GitHub Actions; it is not cryptographically notarized or a
permanent independent registry. Reproducibility uses source hashes.
"""
import csv
import datetime as dt
import hashlib
import json
import re
import unicodedata
from pathlib import Path


def normalize(s):
    return re.sub(r"[^a-z0-9]+","",
        unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore")
        .decode("ascii").lower())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def can_freeze(event_date, now):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Timestamp must carry a timezone")
    return now.astimezone(dt.timezone.utc).date()<dt.date.fromisoformat(event_date)


def make_snapshot(fights, lab, event_date, generated_at, files):
    """Fail closed on fixture and model mismatch. Only future precommitted forecasts."""
    if not can_freeze(event_date,generated_at):
        return {
            "schema":"JSA_EVENT_JOURNAL_V1","eventDate":event_date,
            "generatedAtUTC":generated_at.isoformat(),"status":"NO_PROSPECTIVE_SNAPSHOT",
            "reason":"Event date already started in UTC. Cannot backdate predictions.",
            "predictions":[],"sourceSha256":files
        }
    if lab.get("eventDate")!=event_date or len(fights)!=7 or len(lab.get("upcomingPredictions",[]))!=7:
        raise ValueError("Unexpected event or fighter count")
    rows=[]
    for older,newer in zip(fights,lab["upcomingPredictions"]):
        if (normalize(older.get("red"))!=normalize(newer.get("red")) or
            normalize(older.get("blue"))!=normalize(newer.get("blue"))):
            raise ValueError("UFCash and independent ML fighter identities differ")
        a=float(older["model_p_red"])
        b=newer["probRed"]
        if not 0<a<1 or (b is not None and not 0<float(b)<1):
            raise ValueError("Invalid model probability")
        if newer["passesFrozenConfidenceGate"] and b is None:
            raise ValueError("No probability but model passed confidence gate")
        rows.append({
            "red":newer["red"],"blue":newer["blue"],
            "ufcashProbabilityRed":round(a,7),
            "oddsFreeProbabilityRed":round(float(b),7) if b is not None else None,
            "oddsFreeFrozenGatePassed":bool(newer["passesFrozenConfidenceGate"]),
            "outcome":None,"betPlaced":False,
            "noBettingRecommendation":True
        })
    content={
        "schema":"JSA_EVENT_JOURNAL_V1",
        "eventDate":event_date,
        "generatedAtUTC":generated_at.isoformat(),
        "status":"PRE_EVENT_RESEARCH_ONLY",
        "sourceSha256":files,
        "study":"Prior-sourced UFCash and odds-free model predictions before event date",
        "sourceFreezeScope":"This report seals *model outputs and file checksums*, not underlying third-party historical data",
        "predictionCount":len(rows),"predictions":rows,
        "modelProbabilitiesNotBettingEdges":True,
        "outcomeIndependentVerificationPending":True,
    }
    content["snapshotSha256"]=digest(json.dumps(content,sort_keys=True,
                               separators=(",",":"),ensure_ascii=False).encode("utf-8"))
    return content


def main():
    root=Path(__file__).resolve().parents[1]
    card=root/"card/upcoming.csv"
    ufc=root/"ufcash/results/upcoming_predictions.csv"
    lab=root/"results/precision_lab.json"
    ref=root/"reference.json"
    needed=[card,ufc,lab,ref]
    for path in needed:
        if not path.exists() or not path.is_file():
            raise SystemExit("Missing prospective input: "+str(path))
    contents={str(p.relative_to(root)):digest(p.read_bytes()) for p in needed}
    with card.open(encoding="utf-8",newline="") as f:
        card_rows=list(csv.DictReader(f))
    with ufc.open(encoding="utf-8",newline="") as f:
        fights=list(csv.DictReader(f))
    report=json.loads(lab.read_text(encoding="utf-8"))
    dates={r["date"] for r in card_rows}
    if len(dates)!=1:
        raise SystemExit("Expected precisely one official event date")
    date=next(iter(dates))
    if len(card_rows)!=len(fights) or any(
        normalize(a["red"])!=normalize(b["red"]) or normalize(a["blue"])!=normalize(b["blue"])
        for a,b in zip(card_rows,fights)
    ):
        raise SystemExit("UFCash output and original input card disagree")
    now=dt.datetime.now(dt.timezone.utc)
    obj=make_snapshot(fights,report,date,now,contents)
    folder=root/"results"
    folder.mkdir(exist_ok=True)
    (folder/"prospective_journal.json").write_text(
        json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
        encoding="utf-8")
    print(json.dumps({"status":obj["status"],"eventDate":obj["eventDate"],
       "count":len(obj["predictions"]),"sha256":obj.get("snapshotSha256"),
       "note":"GitHub run timestamp anchors artifact; NOT a permanent notarized record"}))


if __name__=="__main__":
    main()
