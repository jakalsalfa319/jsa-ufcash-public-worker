#!/usr/bin/env python3
"""Prepare an explicitly UNREVIEWED future UFC research-card draft.

Input MUST be a separately prepared UFCash pre-fight feature parquet table.
This script never invents missing fighter data, silently assumes an outcome,
claims an official card is confirmed, or asks the frozen model to predict.

Review the draft's exact fighter pairs, missing data, bout date, source hash,
and official URL BEFORE copying it to cards/reviewed/ and setting status.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

from scripts.precision_lab import FEATURES,RATINGS
from scripts.future_card_inference import utc_timestamp,card_url,canonical


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()


def as_numeric(value):
    import pandas as pd
    if pd.isna(value):
        return None
    try:
        value=float(value)
    except (TypeError,ValueError):
        return None
    return value if math.isfinite(value) and abs(value)<=1e5 else None


def draft(table,event_date,starts_at,url,asof,feature_sha):
    import pandas as pd
    if asof.tzinfo is None or asof.utcoffset() is None:
        raise ValueError("Draft timestamp must be timezone aware")
    event=dt.date.fromisoformat(event_date)
    if event<=dt.date(2026,11,21) or event<asof.date():
        raise ValueError("Previously frozen/historical event date forbidden")
    starts=utc_timestamp(starts_at)
    if starts<=asof:
        raise ValueError("Cannot prepare a draft after event start")
    card_url(url)
    if len(feature_sha)!=64 or any(x not in "0123456789abcdef" for x in feature_sha):
        raise ValueError("Feature parquet source SHA-256 required")
    required={"date","outcome","winner","r_name","b_name","card_pos"}
    required.update({"r_"+k for k in FEATURES})
    required.update({"b_"+k for k in FEATURES})
    required.update(RATINGS)
    missing=required.difference(table.columns)
    if missing:
        raise ValueError("Incomplete upstream UFCash feature columns: "+str(sorted(missing)[:12]))
    df=table.copy()
    df["date"]=pd.to_datetime(df["date"],errors="raise").dt.date
    selected=df.loc[df["date"]==event].sort_values("card_pos")
    if selected.empty or len(selected)>18:
        raise ValueError("Expected 1 to 18 future fights on requested event date")
    if selected.card_pos.duplicated().any():
        raise ValueError("Duplicate future bout positions")
    rows=[];gaps=[];seen=set()
    for i,(_,row) in enumerate(selected.iterrows()):
        winning=as_numeric(row["winner"])
        if row["outcome"]!="UPCOMING" or (winning is not None and winning!=-1.):
            raise ValueError("Future card contains a known/recorded result")
        red=str(row["r_name"]).strip()
        blue=str(row["b_name"]).strip()
        pair=tuple(sorted((canonical(red),canonical(blue))))
        if not all(pair) or pair[0]==pair[1] or pair in seen:
            raise ValueError("Duplicate or invalid future bout")
        seen.add(pair)
        red_features={k:as_numeric(row["r_"+k]) for k in FEATURES}
        blue_features={k:as_numeric(row["b_"+k]) for k in FEATURES}
        rating={k:as_numeric(row[k]) for k in RATINGS}
        unknown=[k for k in FEATURES if red_features[k] is None or blue_features[k] is None]
        unknown +=[k for k in RATINGS if rating[k] is None or not 0<rating[k]<1]
        if unknown:
            gaps.append({"red":red,"blue":blue,"missingOrInvalid":unknown})
        rows.append({
          "red":red,"blue":blue,"status":"UPCOMING","winner":None,
          "redFeatures":red_features,"blueFeatures":blue_features,"ratings":rating
        })
    return {
        "schema":"JSA_REVIEWED_FUTURE_CARD_V1",
        "reviewStatus":"DRAFT",
        "reviewedAtUTC":None,
        "eventDate":event_date,"startsAtUTC":starts.isoformat(),
        "featuresCapturedAtUTC":asof.astimezone(dt.timezone.utc).isoformat(),
        "officialEventUrl":url,
        "featureSource":{"date":asof.astimezone(dt.timezone.utc).isoformat(),
            "description":"UFCash public pre-fight engineered stats; independently review point-in-time provenance",
            "fileSha256":feature_sha,"independentlyAudited":False},
        "missingOrInvalidFeatures":gaps,
        "bouts":rows,
        "draftCaution":"NOT REVIEWED. File content is not official fighter confirmation. Do not label accepted until source, freshness, identities and all nulls independently checked."
    }


def main():
    import pandas as pd
    parser=argparse.ArgumentParser()
    parser.add_argument("--features",required=True,type=Path)
    parser.add_argument("--event",required=True)
    parser.add_argument("--starts-at-utc",required=True)
    parser.add_argument("--official-url",required=True)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite a prepared draft")
    if not args.features.is_file() or args.features.stat().st_size>500_000_000:
        raise SystemExit("Feature parquet unavailable or unreasonably large")
    now=dt.datetime.now(dt.timezone.utc)
    result=draft(pd.read_parquet(args.features),args.event,args.starts_at_utc,
                 args.official_url,now,sha(args.features))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as f:
        f.write(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    print(json.dumps({"status":"DRAFT_ONLY","event":result["eventDate"],
        "fights":len(result["bouts"]),"incomplete":len(result["missingOrInvalidFeatures"]),
        "sourceSha256":result["featureSource"]["fileSha256"],
        "reviewRequired":True,"predictionsGenerated":False}))


if __name__=="__main__":
    main()
