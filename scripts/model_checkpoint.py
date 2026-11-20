#!/usr/bin/env python3
"""Versioned, checksum-gated fitted Frontier v2 model checkpoint.

Research only. The archive stores actual trained sklearn/XGBoost/CatBoost
objects, not a recipe to retrain them. A separately trusted SHA-256 is REQUIRED
before deserializing joblib files: pickles are unsafe from unknown authors.
Identical checkpoint files yield identical predictions in a compatible pinned
runtime. A new model build is a NEW checkpoint, never a silent overwrite.

The checkpoint does not change the existing historical or Nov 21 forecasts.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import importlib.metadata
import io
import json
import math
from pathlib import Path
import tarfile
import tempfile

COMPONENTS=("recent_logistic","hist_boost","xgboost","catboost")
WEIGHTS=(.4,.2,.2,.2)
SCHEMA="JSA_FRONTIER_FITTED_CHECKPOINT_V1"
RAW_EXPECTED={
 "data/raw/canon/canon.db":"8185a2163b5f97071dbc4ec68667cceb43f5e321fadc38c26b5069303af4d949",
 "data/raw/greco/ufc_event_details.csv":"f4d99fec0b5d750cafd9be1892b15d45cacb2ffa37129fbda457b82b5637508b",
 "data/raw/greco/ufc_fight_details.csv":"d63d6b9a576e5fcd28661d6586e0b428ecf8e613b8fc8d64901ca5da410007f2",
 "data/raw/greco/ufc_fight_results.csv":"eb492be1036b3029d21e08269e155f18da7e6af0c0b6e904dbcefb06cf3d14a2",
 "data/raw/greco/ufc_fight_stats.csv":"71881460f3db7ce9ab7a968c25cb2c104964905171180fbe2370d93c10a33e1f",
 "data/raw/greco/ufc_fighter_details.csv":"5b3c8e9fe1adffc6a136ef90fb0f7b0cb342b1bda0badbb4406ddd22aa0472b0",
 "data/raw/greco/ufc_fighter_tott.csv":"d8d0a75556a86a18b236916fc67bb581385f7c72361ac3e83ade6a121c362fdc",
 "data/raw/nlbair/ufc_all_fights_wide.parquet":"88cf59f50e2a0dce7291ab5abefe155a5f30969178c2c14c0e51927144a48bf6",
 "data/raw/ultimate/ufc-master.csv":"b8aa6604539d5981bba561cb65da26133567732145ca48efbec2d9423b081937",
}
SOURCE_FILES=("scripts/accuracy_frontier.py","scripts/precision_lab.py",
              "scripts/rolling_2026.py","scripts/model_checkpoint.py")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()


def source_hashes(root):
    current={}
    for path,expected in RAW_EXPECTED.items():
        full=Path(root)/"ufcash"/path
        if not full.is_file():
            raise ValueError("Missing historic source required for frozen fit: "+path)
        actual=sha256_file(full)
        if actual!=expected:
            raise ValueError("Source changed; frozen dataset fingerprint mismatch: "+path)
        current[path]=actual
    return current


def combine(models,x,slope):
    """Same antisymmetric ensemble and symmetric Platt calibration as Frontier v2."""
    import numpy as np
    from scripts.precision_lab import symmetric_prediction
    if tuple(models)!=COMPONENTS:
        raise ValueError("Fitted model component contract mismatch")
    x=np.asarray(x,dtype=float)
    if x.ndim!=2 or not np.all(np.isfinite(x)):
        raise ValueError("Nonfinite or wrong-dimensional feature matrix")
    if not math.isfinite(float(slope)) or slope<=0:
        raise ValueError("Invalid frozen Platt slope")
    values=[symmetric_prediction(models[name],x) for name in COMPONENTS]
    raw=sum(w*p for w,p in zip(WEIGHTS,values))
    raw=np.clip(raw,1e-4,1-1e-4)
    logits=np.log(raw/(1-raw))
    return 1/(1+np.exp(-np.clip(float(slope)*logits,-40,40)))


def export_checkpoint(root,models,feature_names,validation_x,expected_validation,
                      slope,gate,historical_correct):
    import numpy as np
    import joblib
    root=Path(root)
    if tuple(models)!=COMPONENTS:
        raise ValueError("Model list/ordering changed")
    if len(feature_names)!=50 or len(set(feature_names))!=50:
        raise ValueError("Upstream feature schema must contain expected 50 distinct values")
    if not (0.5<=gate<=0.85):
        raise ValueError("Confidence gate outside frozen validation contract")
    x=np.asarray(validation_x,dtype=float)
    expected=np.asarray(expected_validation,dtype=float)
    if x.ndim!=2 or x.shape[1]!=len(feature_names)+6 or len(x)!=len(expected) or len(x)<90:
        raise ValueError("Missing/changed validation fixture matrix")
    actual=combine(models,x,slope)
    if not np.allclose(actual,expected,atol=2e-10,rtol=0):
        raise ValueError("Fitted checkpoint cannot reproduce original calibration")
    hashes=source_hashes(root)
    out=root/"results"
    out.mkdir(parents=True,exist_ok=True)
    archive=out/"frozen_frontier_v2_checkpoint.tar.gz"
    receipt=out/"frozen_frontier_v2_receipt.json"
    chosen_ix=sorted(set(list(range(0,min(12,len(x))))+
                         list(range(max(0,len(x)-12),len(x)))))
    versions={}
    for package in ("numpy","scikit-learn","xgboost","catboost","joblib","pandas","pyarrow"):
        versions[package]=importlib.metadata.version(package)
    manifest={
      "schema":SCHEMA,
      "model":"Frontier v2: 40% recent logistic, 20% HistGradientBoosting, 20% XGBoost, 20% CatBoost",
      "trainedUsing":"2012-2024, original UFCash pre-fight historical features",
      "calibratedUsing":"2025 Jan-Jun pre-fight and fight results only",
      "selectedUsing":"2025 Jul-Dec Brier and Wilson confidence rule",
      "selectionMadeWithout2026Outcomes":True,
      "trainingSourceSha256":hashes,
      "trainedFeatureTableSha256":sha256_file(root/"ufcash/data/processed/features.parquet"),
      "sourceCodeSha256":{p:sha256_file(root/p) for p in SOURCE_FILES},
      "originalFeatureNames":list(feature_names),
      "derivedInteractionFeatures":6,
      "modelComponents":list(COMPONENTS),
      "ensembleWeights":list(WEIGHTS),
      "symmetricPlattSlope":float(slope),
      "gateThreshold":float(gate),
      "packages":versions,
      "historical2026Correct":int(historical_correct),
      "historical2026Eligible":266,
      "historicalEvaluationNote":"Already examined retrospective development cohort. Accuracy is run-specific, not validated live prediction edge.",
      "sampleFixture":{
        "x":[[float(v) for v in x[i]] for i in chosen_ix],
        "expectedProbability":[float(expected[i]) for i in chosen_ix],
        "indices":chosen_ix
      },
      "files":{},
      "noBetsPlaced":True,
      "profitsVerified":False,
      "doNotTrustUnverifiedPickle":True,
    }
    archive_members={}
    for name in COMPONENTS:
        # The objects in this bundle are the ACTUAL already-fitted objects.
        buff=io.BytesIO()
        joblib.dump(models[name],buff,compress=3)
        data=buff.getvalue()
        if len(data)>35_000_000:
            raise ValueError("Unexpectedly large model checkpoint")
        filename="models/"+name+".joblib"
        archive_members[filename]=data
        manifest["files"][filename]={"sha256":sha256_bytes(data),"bytes":len(data)}
    archive_members["manifest.json"]=(json.dumps(
        manifest,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
    with tarfile.open(archive,"w:gz") as tar:
        for name in sorted(archive_members):
            data=archive_members[name]
            info=tarfile.TarInfo(name)
            info.size=len(data)
            info.mode=0o644
            info.mtime=0
            info.uid=info.gid=0
            info.uname=info.gname=""
            tar.addfile(info,io.BytesIO(data))
    digest=sha256_file(archive)
    # A restored, locally-produced archive must predict the same fixture
    # before a receipt may be written. Never trust an arbitrary pickle.
    restored=load_checkpoint(archive,digest)
    if not np.allclose(combine(restored["models"],x,slope),expected,atol=2e-10,rtol=0):
        raise ValueError("Reloaded fitted models produced different predictions")
    release={
      "schema":"JSA_FRONTIER_FROZEN_RECEIPT_V1",
      "archive":"frozen_frontier_v2_checkpoint.tar.gz",
      "archiveSha256":digest,
      "manifestSha256":sha256_bytes(archive_members["manifest.json"]),
      "model":"Frontier v2 selected 2025 H2",
      "historic2026Correct":int(historical_correct),
      "historic2026Eligible":266,
      "validity":"Verified restore of one fitted model snapshot, not repeatability of rebuilding it",
      "inputSourcesCount":len(hashes),
      "fixtureReplayed":len(chosen_ix),
      "requiresPinnedDependencies":versions,
      "externalDownloadTrustRequired":True,
      "prospectiveAccuracyVerified":False,
      "profitVerified":False,
      "betPlaced":False
    }
    receipt.write_text(json.dumps(release,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return release


def load_checkpoint(path,expected_sha256):
    """Load ONLY a pretrusted SHA-pinned artifact; joblib unpickling executes code."""
    import joblib
    if not isinstance(expected_sha256,str) or len(expected_sha256)!=64 or any(
        c not in "0123456789abcdef" for c in expected_sha256):
        raise ValueError("Expected external trusted lowercase SHA-256 is required")
    if sha256_file(path)!=expected_sha256:
        raise ValueError("Checkpoint archive SHA-256 mismatch; refusing deserialization")
    with tarfile.open(path,"r:gz") as tar:
        entries=tar.getmembers()
        names={e.name for e in entries}
        expected={"manifest.json"}|{"models/"+name+".joblib" for name in COMPONENTS}
        if names!=expected or len(entries)!=len(expected):
            raise ValueError("Unexpected archive members")
        if any(not e.isfile() or e.size>35_000_000 for e in entries):
            raise ValueError("Unsafe or oversized checkpoint archive")
        manifest=json.loads(tar.extractfile("manifest.json").read())
        if (manifest.get("schema")!=SCHEMA or
            tuple(manifest.get("modelComponents",[]))!=COMPONENTS or
            manifest.get("ensembleWeights")!=list(WEIGHTS)):
            raise ValueError("Model checkpoint manifest contract mismatch")
        # Explicit allowlist and no path extraction: inspect exact member bytes.
        files={}
        for name in COMPONENTS:
            fn="models/"+name+".joblib"
            data=tar.extractfile(fn).read()
            spec=manifest["files"][fn]
            if sha256_bytes(data)!=spec["sha256"] or len(data)!=spec["bytes"]:
                raise ValueError("Checkpoint model object hash mismatch")
            files[fn]=data
    with tempfile.TemporaryDirectory(prefix="jsa-frozen-model-") as temp:
        models={}
        for name in COMPONENTS:
            fn=Path(temp)/(name+".joblib")
            fn.write_bytes(files["models/"+name+".joblib"])
            models[name]=joblib.load(fn)
        x=manifest["sampleFixture"]["x"]
        target=manifest["sampleFixture"]["expectedProbability"]
        import numpy as np
        result=combine(models,x,manifest["symmetricPlattSlope"])
        if not np.allclose(result,target,atol=2e-10,rtol=0):
            raise ValueError("Archived model fixture probabilities changed")
    return {"manifest":manifest,"models":models}


def infer(archive,expected_sha256,features_file,event_date,output):
    import pandas as pd
    from scripts.precision_lab import read_input
    from scripts.accuracy_frontier import interactions
    dt.date.fromisoformat(event_date)
    bundle=load_checkpoint(archive,expected_sha256)
    manifest=bundle["manifest"]
    table=pd.read_parquet(features_file)
    if "date" not in table or "outcome" not in table or "winner" not in table:
        raise ValueError("Missing future-event evidence fields")
    table["date"]=pd.to_datetime(table["date"])
    rows=table.loc[(table.date==pd.Timestamp(event_date))&
                   (table.outcome=="UPCOMING")].sort_values("card_pos")
    if rows.empty:
        raise ValueError("No explicitly UPCOMING target event bouts")
    if any(v in (0,1) for v in rows.winner):
        raise ValueError("Cannot score a card with known results")
    xx,feature_names=read_input(rows)
    if list(feature_names)!=manifest["originalFeatureNames"]:
        raise ValueError("Upstream pre-fight feature schema changed")
    xx=interactions(xx,feature_names)
    model_p=combine(bundle["models"],xx,manifest["symmetricPlattSlope"])
    result=[]
    for i,row in enumerate(rows.itertuples(index=False)):
        enough=bool(row.r_n_fights>=3 and row.b_n_fights>=3)
        p=float(model_p[i])
        result.append({
          "red":str(row.r_name),"blue":str(row.b_name),"date":event_date,
          "probabilityRed":round(p,8) if enough else None,
          "eligible":enough,"passesFrozenResearchGate":bool(enough and
                   max(p,1-p)>=manifest["gateThreshold"]),
          "winner":None,"betPlaced":False
        })
    report={
      "schema":"JSA_FROZEN_FRONTIER_INFERENCE_V1",
      "eventDate":event_date,"checkpointSha256":expected_sha256,
      "trainedThrough":"2024-12-31","calibrated":"2025-H1",
      "selected":"2025-H2","predictions":result,
      "eventCardOfficiallyVerified":False,"resultsVerified":False,
      "wagersPlaced":False,"researchOnly":True
    }
    path=Path(output)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise ValueError("Refusing to overwrite existing frozen predictions")
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive",required=True)
    p.add_argument("--sha256",required=True,help="SHA-256 copied from trusted signed-off frozen checkpoint receipt")
    p.add_argument("--features",required=True)
    p.add_argument("--event",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    out=infer(a.archive,a.sha256,a.features,a.event,a.output)
    print(json.dumps({"checkpoint":out["checkpointSha256"],"predictions":len(out["predictions"]),
                     "note":"Research only. Results and event sources not yet verified."}))


if __name__=="__main__":
    main()
