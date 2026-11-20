#!/usr/bin/env python3
"""Frontier Stable v4: replace run-variable HistGradientBoosting with stable XGB/Cat.

This is a PREDECLARED 0.40 logistic / 0.30 XGBoost / 0.30 CatBoost research
challenger. It uses exactly the original 2012-2024 trained models and 2025-H1
calibration; no 2026 labels affect training, weights, selection or confidence.
2025-H2 compares fixed v4 vs archived same-run v2. 2026 was already inspected
and is an exploratory replay, NOT a sealed independent prospective evaluation.

Even a pass cannot promote actual wagering or overwrite immutable 21 Nov cards.
"""
from __future__ import annotations
import json
import hashlib
from pathlib import Path

import numpy as np
from scripts.precision_lab import summary
from scripts.accuracy_frontier import symmetric_platt
from scripts.rolling_2026 import ece,paired_event_bootstrap

WEIGHTS={"recent_logistic":.40,"xgboost":.30,"catboost":.30}
REQUIRED=("cal","dev","test")
MIN_DEV_BRIER_GAIN=.001
MAX_DEV_ACCURACY_DROP=.02
THRESHOLD=.65


def valid_source(source,old):
    if source.get("schema")!="JSA_FRONTIER_COMPONENTS_V1" or old.get("schema")!="JSA_FRONTIER_CASES_V1":
        raise ValueError("Unrecognized source model or component schema")
    if old.get("model")!="nonlinear_ensemble":
        raise ValueError("Expected original Frontier v2 baseline")
    for period,n in (("cal",139),("dev",146),("test",266)):
        p=source.get("periods",{}).get(period,{})
        if len(p.get("fightIds",[]))!=n or len(p.get("dates",[]))!=n or len(p.get("outcomeA",[]))!=n:
            raise ValueError("Reproducibility input cohort count changed: "+period)
        if len(set(p["fightIds"]))!=n:
            raise ValueError("Duplicate IDs in source components")
        if len(set(p["outcomeA"])-{0,1}):
            raise ValueError("Unexpected undecided outcome")
        if not all(k in p.get("raw",{}) and len(p["raw"][k])==n for k in WEIGHTS):
            raise ValueError("Missing one of the three trusted component series")
        target_year=2025 if period in ("cal","dev") else 2026
        if any(not date.startswith(str(target_year)+"-") for date in p["dates"]):
            raise ValueError("Wrong chronology in "+period)
        if period=="cal" and any(date>="2025-07-01" for date in p["dates"]):
            raise ValueError("Calibration contaminated with later outcomes")
        if period=="dev" and any(not "2025-07-01"<=date<"2026-01-01" for date in p["dates"]):
            raise ValueError("2025 H2 validation boundaries violated")
        if period=="test" and any(not "2026-01-01"<=date<"2026-11-19" for date in p["dates"]):
            raise ValueError("2026 prior-outcomes boundaries violated")
        for k in WEIGHTS:
            vals=np.asarray(p["raw"][k],dtype=float)
            if not np.all(np.isfinite(vals)) or np.any((vals<=0)|(vals>=1)):
                raise ValueError("Invalid component "+k)
    for name,period in (("selection2025","dev"),("development2026","test")):
        old_rows=old.get(name,[])
        if len(old_rows)!=len(source["periods"][period]["fightIds"]):
            raise ValueError("Old v2 matched cohort size changed")
        lookup={r["id"]:r for r in old_rows}
        for id,y in zip(source["periods"][period]["fightIds"],source["periods"][period]["outcomeA"]):
            if id not in lookup or lookup[id]["winnerA"]!=y:
                raise ValueError("v2 and stable v4 same-fight identity/outcome mismatch")
    return True


def blend(rows):
    p=rows["raw"]
    return sum(float(w)*np.asarray(p[name],dtype=float) for name,w in WEIGHTS.items())


def validate_frozen_gate(base,proposed,truth):
    old=summary(np.asarray(base,dtype=float).tolist(),list(truth))
    new=summary(np.asarray(proposed,dtype=float).tolist(),list(truth))
    passed=(new["brier"]<=old["brier"]-MIN_DEV_BRIER_GAIN and
            new["accuracy"]>=old["accuracy"]-MAX_DEV_ACCURACY_DROP)
    return passed,old,new


def audit(source,cases):
    valid_source(source,cases)
    periods=source["periods"]
    # Calibration uses early 2025 only. Exactly one Platt slope, no extra tuning.
    p_cal=blend(periods["cal"])
    y_cal=np.asarray(periods["cal"]["outcomeA"],dtype=int)
    p_dev,slope=symmetric_platt(p_cal,y_cal,blend(periods["dev"]))
    p_test,_=symmetric_platt(p_cal,y_cal,blend(periods["test"]))
    def original(name):
        section="selection2025" if name=="dev" else "development2026"
        lookup={r["id"]:r for r in cases[section]}
        rows=periods[name]
        return np.array([lookup[id]["probabilities"]["nonlinear_ensemble"]
                         for id in rows["fightIds"]],dtype=float)
    b_dev=original("dev")
    b_test=original("test")
    passed,valold,valnew=validate_frozen_gate(b_dev,p_dev,periods["dev"]["outcomeA"])
    labels=periods["test"]["outcomeA"]
    v2=summary(b_test.tolist(),labels)
    v4=summary(p_test.tolist(),labels)
    v2["ece10"]=ece(b_test,np.asarray(labels,dtype=int))
    v4["ece10"]=ece(p_test,np.asarray(labels,dtype=int))
    selected=summary(p_test.tolist(),labels,THRESHOLD)
    selected_b=summary(b_test.tolist(),labels,THRESHOLD)
    in_v4=np.maximum(p_test,1-p_test)>=THRESHOLD
    v2_same_subset=summary(b_test[in_v4].tolist(),np.asarray(labels)[in_v4].tolist())
    delta=100*(v4["accuracy"]-v2["accuracy"])
    ci=paired_event_bootstrap(p_test,b_test,np.asarray(labels),
                               periods["test"]["dates"],reps=800)
    # 8-decimal fingerprints capture meaningful score changes while avoiding
    # benign 1e-12 numerical jitter in logistic calibration.
    digest=lambda vec:hashlib.sha256(np.round(np.asarray(vec,dtype=float),8).astype("<f8").tobytes()).hexdigest()
    signatures={name:digest(periods["test"]["raw"][name]) for name in WEIGHTS}
    signatures["stable2026"]=digest(p_test)
    report={
      "schema":"JSA_FRONTIER_STABLE_V4",
      "policy":"Fixed 40% recent logistic + 30% XGBoost + 30% CatBoost; unstable HistGradientBoosting EXCLUDED",
      "trainCutoff":"2024-12-31","calibration2025H1Count":139,
      "validation2025H2Count":146,"diagnostic2026Count":266,
      "originalModelPreserved":True,"frozenForecastsPreserved":True,
      "sameSourceSamples":True,
      "validation2025H2":{"passed":passed,"v2":valold,"stable":valnew},
      "lockedRule":"2025 H2 Brier <= original minus 0.001 and accuracy not lower by >2pp",
      "calibrationSlope":slope,
      "sameFight2026":{"originalV2":v2,"stableV4":v4,
           "accuracyDifferencePp":round(delta,4),
           "pairedEventBootstrap95Pp":[round(100*x,3) for x in ci]},
      "selective2026AtOriginal65":{"originalV2":selected_b,"stableV4":selected,
          "originalV2OnStableSelectedSubset":v2_same_subset},
      "reproducibilitySignaturesSha256":signatures,
      "noPolicyPromotion":True,"newProspectiveEvidenceRequired":True,
      "alreadyExamined2026":True,"betsPlaced":False,"profitEdgeVerified":False,
      "accuracy99_9Verified":False,
      "warning":"This retrospective already-examined 2026 cohort cannot establish stable out-of-sample gains; incomplete point-in-time source audit and market prices."
    }
    return report


def main():
    root=Path(__file__).resolve().parents[1]
    raw=json.loads((root/"results/frontier_components.json").read_text())
    old=json.loads((root/"results/frontier_cases.json").read_text())
    report=audit(raw,old)
    dest=root/"results/stable_frontier_v4.json"
    dest.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({"2025passed":report["validation2025H2"]["passed"],
       "2025v2Brier":report["validation2025H2"]["v2"]["brier"],
       "2025stableBrier":report["validation2025H2"]["stable"]["brier"],
       "2026v2":report["sameFight2026"]["originalV2"]["accuracy"],
       "2026stable":report["sameFight2026"]["stableV4"]["accuracy"],
       "2026gainPP":report["sameFight2026"]["accuracyDifferencePp"],
       "2026stableCorrect":report["sameFight2026"]["stableV4"]["correct"],
       "2026selected":report["selective2026AtOriginal65"]["stableV4"],
       "researchOnly":True},indent=2))


if __name__=="__main__":
    main()
