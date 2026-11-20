#!/usr/bin/env python3
"""J$A frozen-model upcoming-event inference, NO training and NO betting.

Use only a reviewed event-card JSON with complete *pre-event* fighter features.
The official UFC HTML must be fetched afresh and both tracked names must occur
in the same individual bout, never only elsewhere on the page. A saved official
URL in a JSON file alone is NOT verification.

The statistical source of the features (UFCash-derived or independently
prepared) is NOT proven point-in-time by a URL or user input: outputs mark that
limitation explicitly and require review before any accuracy/profit claim.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import ipaddress
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import unicodedata

SCHEMA="JSA_REVIEWED_FUTURE_CARD_V1"
OUTPUT_SCHEMA="JSA_FROZEN_FRONTIER_FUTURE_INFERENCE_V1"
RELEASE_TAG="jsa-frontier-v2-fitted-2026-11-20"
TRUSTED_SHA="727b4a535927157257de84f6a7cc3fd5988aba9cabb98ba6bf84e726dc1a3a97"
RESTRICTED_DATE=dt.date(2026,11,21)
MAX_BOUTS=18
MAX_HTML_BYTES=1_500_000
APPROVED_HOSTS=("ufc.com","www.ufc.com")


def utc_timestamp(value):
    if not isinstance(value,str):
        raise ValueError("An explicit ISO-8601 UTC timestamp is required")
    try:
        parsed=dt.datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError("Malformed ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp must contain timezone")
    return parsed.astimezone(dt.timezone.utc)


def canonical(value):
    value=unicodedata.normalize("NFKD",str(value))
    return re.sub("[^a-z0-9]","",value.encode("ascii","ignore").decode().lower())


def card_url(url):
    if not isinstance(url,str) or len(url)>350:
        raise ValueError("Invalid official event URL")
    p=urlsplit(url)
    if (p.scheme!="https" or p.hostname not in APPROVED_HOSTS or
        p.username or p.password or p.port not in (None,443) or
        not p.path.startswith("/event/") or p.query or p.fragment):
        raise ValueError("Only direct HTTPS UFC event-page URLs are permitted")
    return url


def official_html(url):
    url=card_url(url)
    req=Request(url,headers={"Accept":"text/html","User-Agent":"JSA-Frozen-Card-Integrity/1.0"})
    with urlopen(req,timeout=18) as resp:
        if card_url(resp.geturl())!=url:
            raise ValueError("Official card redirected; verify changed URL manually")
        data=resp.read(MAX_HTML_BYTES+1)
    if not 3500<=len(data)<=MAX_HTML_BYTES:
        raise ValueError("Incomplete or excessive UFC page response")
    return data.decode("utf-8","replace"),hashlib.sha256(data).hexdigest()


def verified_bouts(html,bouts):
    from scripts.card_integrity import BoutParser
    parser=BoutParser()
    parser.feed(html)
    tracked=[(canonical(b["red"]),canonical(b["blue"])) for b in bouts]
    for i,(red,blue) in enumerate(tracked):
        if not red or not blue or red==blue:
            raise ValueError("Invalid opponent identity")
        matches=0
        for block in parser.bouts:
            plain=canonical(block)
            if red not in plain or blue not in plain:
                continue
            # Prevent a parent <li> or card navigation from matching all fights.
            foreign=[f for j,pair in enumerate(tracked) if j!=i for f in pair]
            if any(f in plain for f in foreign):
                continue
            matches+=1
        if matches!=1:
            raise ValueError("Official source cannot verify EXACT same-bout matchup "+
                             bouts[i]["red"]+" vs "+bouts[i]["blue"])
    return True


def valid_card(card,now,feature_names):
    from scripts.precision_lab import FEATURES,RATINGS
    if card.get("schema")!=SCHEMA:
        raise ValueError("Unexpected future-card schema")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("The inference clock requires timezone")
    event=dt.date.fromisoformat(card["eventDate"])
    if event<=RESTRICTED_DATE or event<now.date():
        raise ValueError("Historical/previously frozen card must never be reissued")
    starts=utc_timestamp(card["startsAtUTC"])
    captured=utc_timestamp(card["featuresCapturedAtUTC"])
    if starts<=now or captured>now or captured>=starts:
        raise ValueError("Future event and pre-event feature timestamps required")
    if card.get("reviewStatus")!="REVIEWED":
        raise ValueError("Only manually reviewed card snapshots may be inferred")
    reviewed=utc_timestamp(card.get("reviewedAtUTC"))
    if not (captured<=reviewed<=now and reviewed<starts):
        raise ValueError("Card review must follow source capture and precede event")

    if abs((starts.date()-event).days)>1:
        raise ValueError("UTC start too far from declared local event date")
    if captured<now-dt.timedelta(days=45):
        raise ValueError("Feature snapshot is older than 45 days")
    url=card_url(card.get("officialEventUrl"))
    if "date" not in card.get("featureSource",{}):
        raise ValueError("Feature-source reference must identify collection date")
    src=card["featureSource"]
    if not isinstance(src.get("description"),str) or len(src["description"].strip())<12:
        raise ValueError("Feature provenance requires meaningful description")
    if utc_timestamp(src["date"])>captured:
        raise ValueError("Feature-source timestamp cannot postdate captured features")
    bout_list=card.get("bouts")
    if not isinstance(bout_list,list) or not 1<=len(bout_list)<=MAX_BOUTS:
        raise ValueError("Expected one to 18 unscored bouts")
    expected=set(FEATURES)
    seen=set()
    if len(feature_names)!=len(FEATURES)+len(RATINGS):
        raise ValueError("Checkpoint has unexpected feature count")
    for b in bout_list:
        if not isinstance(b,dict):
            raise ValueError("Invalid bout record")
        red=b.get("red");blue=b.get("blue")
        if not all(isinstance(n,str) and 2<=len(n.strip())<=100 for n in (red,blue)):
            raise ValueError("Fighter names must be explicitly reviewed")
        pair=tuple(sorted((canonical(red),canonical(blue))))
        if not pair[0] or pair[0]==pair[1] or pair in seen:
            raise ValueError("Repeated or invalid fighter pair")
        seen.add(pair)
        for side in ("redFeatures","blueFeatures"):
            obj=b.get(side)
            if not isinstance(obj,dict) or set(obj)!=expected:
                raise ValueError("Missing, additional or disallowed fighter features")
            for k,v in obj.items():
                if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>1e5:
                    raise ValueError("Non-finite or out-of-range pre-fight statistic "+k)
        rating=b.get("ratings")
        if not isinstance(rating,dict) or set(rating)!=set(RATINGS):
            raise ValueError("Missing full set of pre-event rating probabilities")
        for key,val in rating.items():
            if isinstance(val,bool) or not isinstance(val,(int,float)) or not math.isfinite(val) or not 0<val<1:
                raise ValueError("Invalid red-side pre-fight rating "+key)
        if b.get("winner") is not None or b.get("status") not in (None,"UPCOMING"):
            raise ValueError("Known outcomes or cancelled fights prohibited")
    return url


def to_matrix(card,original_feature_names):
    import pandas as pd
    from scripts.precision_lab import FEATURES,RATINGS,read_input
    from scripts.accuracy_frontier import interactions
    df=pd.DataFrame([{**{"r_"+k:b["redFeatures"][k] for k in FEATURES},
                     **{"b_"+k:b["blueFeatures"][k] for k in FEATURES},
                     **b["ratings"]} for b in card["bouts"]])
    features,names=read_input(df)
    if list(names)!=list(original_feature_names):
        raise ValueError("Frozen model feature contract differs from card data")
    xx=interactions(features,names)
    if xx.shape!=(len(card["bouts"]),len(original_feature_names)+6):
        raise ValueError("Interaction vector dimensions changed")
    return xx


def forecast(card,checkpoint,model_sha,asof,source_html=None,source_sha=None):
    from scripts.model_checkpoint import combine
    if model_sha!=TRUSTED_SHA:
        raise ValueError("Model release identifier is not the signed-off approved SHA")
    manifest=checkpoint["manifest"]
    if manifest.get("schema")!="JSA_FRONTIER_FITTED_CHECKPOINT_V1":
        raise ValueError("Unexpected fitted-model schema")
    if manifest.get("ensembleWeights")!=[.4,.2,.2,.2] or manifest.get("gateThreshold")!=.65:
        raise ValueError("Approved model coefficients or confidence gate changed")
    url=valid_card(card,asof,manifest["originalFeatureNames"])
    if source_html is None or not source_sha:
        raise ValueError("Independent current official event HTML verification required")
    verified_bouts(source_html,card["bouts"])
    # Model numbers are generated only after exact-bout official-source checks.
    matrix=to_matrix(card,manifest["originalFeatureNames"])
    values=combine(checkpoint["models"],matrix,manifest["symmetricPlattSlope"])
    predictions=[]
    for b,p in zip(card["bouts"],values):
        sufficient=min(b["redFeatures"]["n_fights"],b["blueFeatures"]["n_fights"])>=3
        p=float(p)
        predictions.append({
          "red":b["red"],"blue":b["blue"],
          "probabilityRed":round(p,8) if sufficient else None,
          "eligible":bool(sufficient),
          "passesFrozenResearchGate":bool(sufficient and max(p,1-p)>=.65),
          "winner":None,"betPlaced":False,"recommendedBet":False,
        })
    without_hash={
      "schema":OUTPUT_SCHEMA,"eventDate":card["eventDate"],
      "officialEventUrl":url,"observedAtUTC":asof.isoformat(),
      "officialHtmlSha256":source_sha,
      "inputSnapshotSha256":hashlib.sha256(
            json.dumps(card,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest(),
      "modelReleaseTag":RELEASE_TAG,"checkpointArchiveSha256":model_sha,
      "featureContract":"50 frozen pre-fight inputs and 6 derived interactions",
      "modelTrainedThrough":"2024-12-31","modelCalibratedUsing":"2025 H1",
      "predictions":predictions,"officialBoutsMatched":len(predictions),
      "featureContentsIndependentlyAudited":False,
      "eventCardOfficiallyVerifiedAtFetch":True,
      "fightResultsVerified":False,"moneyWagered":False,
      "researchOnly":True,
      "warning":"Official bout listing verified. Supplied pre-event feature values have not been independently audited. NOT executable odds or a betting/profit recommendation."
    }
    without_hash["snapshotSha256"]=hashlib.sha256(json.dumps(
        without_hash,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
    return without_hash


def main():
    from scripts.model_checkpoint import load_checkpoint
    parser=argparse.ArgumentParser()
    parser.add_argument("--archive",required=True,type=Path)
    parser.add_argument("--input",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to rewrite existing forecast")
    if not args.input.is_file() or args.input.stat().st_size>500_000:
        raise SystemExit("Reviewed card JSON unavailable or too large")
    card=json.loads(args.input.read_text(encoding="utf-8"))
    now=dt.datetime.now(dt.timezone.utc)
    # No deserialization until card syntax/time and SHA checks are fulfilled.
    from scripts.precision_lab import FEATURES,RATINGS
    valid_card(card,now,list(FEATURES)+list(RATINGS))
    html,html_sha=official_html(card["officialEventUrl"])
    bundle=load_checkpoint(args.archive,TRUSTED_SHA)
    result=forecast(card,bundle,TRUSTED_SHA,now,html,html_sha)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as handle:
        handle.write(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    print(json.dumps({"eventDate":result["eventDate"],"verifiedBouts":len(result["predictions"]),
       "researchGatePassed":sum(x["passesFrozenResearchGate"] for x in result["predictions"]),
       "snapshotSha256":result["snapshotSha256"],"researchOnly":True}))


if __name__=="__main__":
    main()
