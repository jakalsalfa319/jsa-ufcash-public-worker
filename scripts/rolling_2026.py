#!/usr/bin/env python3
"""Chronological 2026 UFC model-diversity experiment.

The *policy definition* is frozen in code before running this comparison.
Scores on 2026 are a development-period replay already inspected by the owner,
NOT a genuinely untouched test and NOT prospective proof. Every quarterly
prediction uses ONLY results from earlier quarters. No odds as features.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

from scripts.precision_lab import (
    read_input, algorithm, symmetric_prediction, summary, FEATURES, RATINGS,
)

# Fixed before scoring this retrospective 2026 replay.
FAMILIES = ("logistic_weak", "hist_boost", "xgboost", "catboost")
QUARTERS = (
    ("2026-01-01", "2025-10-01", "2026-04-01"),
    ("2026-04-01", "2026-01-01", "2026-07-01"),
    ("2026-07-01", "2026-04-01", "2026-10-01"),
    ("2026-10-01", "2026-07-01", "2026-11-19"),
)
SELECTION_THRESHOLD = .75
MIN_PRECAL_FIGHTS = 35
SEED = 20261119


def make_candidate(name):
    if name in ("logistic_weak", "hist_boost"):
        return algorithm(name)
    if name == "xgboost":
        from xgboost import XGBClassifier
        return XGBClassifier(
            n_estimators=160, max_depth=3, learning_rate=.045,
            subsample=.85, colsample_bytree=.85, reg_lambda=10,
            min_child_weight=8, tree_method="hist", n_jobs=2,
            random_state=SEED, eval_metric="logloss",
        )
    if name == "catboost":
        from catboost import CatBoostClassifier
        return CatBoostClassifier(
            iterations=180, depth=4, learning_rate=.045,
            l2_leaf_reg=9, loss_function="Logloss", thread_count=2,
            verbose=False, random_seed=SEED, allow_writing_files=False,
        )
    raise ValueError("Unexpected family: " + str(name))


def canonical_date(text):
    return dt.date.fromisoformat(str(text)[:10])


def validate_temporal(train_dates, calib_dates, eval_dates, calibration_start, cutoff):
    """Enforce no same-date or after-event training/calibration leakage."""
    pre = canonical_date(calibration_start)
    split = canonical_date(cutoff)
    if not (len(train_dates) and len(calib_dates) and len(eval_dates)):
        raise ValueError("Empty train, prior calibration or evaluation cohort")
    if not (max(train_dates) < pre and min(calib_dates) >= pre
            and max(calib_dates) < split and min(eval_dates) >= split):
        raise ValueError("Temporal boundary violation")


def calibrate_prior(raw_cal, y_cal, raw_future):
    """A single symmetric Platt slope, estimated only before the target quarter."""
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    if len(y_cal) < MIN_PRECAL_FIGHTS:
        raise ValueError("Insufficient prior calibration period")
    z = lambda x: np.log(np.clip(x,1e-4,1-1e-4) /
                         (1-np.clip(x,1e-4,1-1e-4))).reshape(-1,1)
    model = LogisticRegression(C=.5, fit_intercept=False, max_iter=700)
    model.fit(np.vstack([z(raw_cal),-z(raw_cal)]),
              np.r_[y_cal,1-y_cal])
    return model.predict_proba(z(raw_future))[:,1],float(model.coef_[0,0])


def ece(prob, labels, bins=10):
    import numpy as np
    p=np.asarray(prob,dtype=float)
    y=np.asarray(labels,dtype=int)
    if not len(y):return None
    group=np.minimum(bins-1,(p*bins).astype(int))
    return float(sum((np.sum(group==i)/len(y)) *
                     abs(float(p[group==i].mean())-float(y[group==i].mean()))
                     for i in range(bins) if np.any(group==i)))


def score(p,y,threshold=.5):
    d=summary(list(p),list(y),threshold)
    d["ece_10bins"]=ece([a for a in p],[b for b in y]) if threshold==.5 else (
        ece([float(q) for q in p if max(float(q),1-float(q))>=threshold],
            [int(v) for q,v in zip(p,y) if max(float(q),1-float(q))>=threshold])
    )
    return d


def paired_event_bootstrap(a,b,y,dates,reps=1200):
    """Exploratory event-clustered accuracy delta interval; not a p-value."""
    import numpy as np
    from collections import defaultdict
    by_event=defaultdict(list)
    for i,day in enumerate(dates):
        by_event[str(day)].append(i)
    blocks=list(by_event.values())
    rng=np.random.default_rng(SEED)
    diff=[]
    for _ in range(reps):
        picks=rng.integers(0,len(blocks),len(blocks))
        ix=np.array([i for j in picks for i in blocks[j]],dtype=int)
        aa=(np.asarray(a)[ix]>=.5)==np.asarray(y)[ix]
        bb=(np.asarray(b)[ix]>=.5)==np.asarray(y)[ix]
        diff.append(float(aa.mean()-bb.mean()))
    return [float(v) for v in np.percentile(diff,[2.5,97.5])]


def evaluate(past):
    import numpy as np
    import pandas as pd
    frame=past.copy()
    if frame.fight_id.duplicated().any():
        raise ValueError("Duplicate fighter bout identifiers in historical feature table")
    features,feat_names=read_input(frame)
    y=frame.winner.astype(int).to_numpy()
    dates=frame.date.to_numpy()
    rows=[]
    traces={name:[] for name in FAMILIES}
    selection=[]
    # Fixed static reference: 2012-2023 training, 2024 Platt calibration.
    train_mask=(frame.date<pd.Timestamp("2024-01-01")).to_numpy()
    validation_mask=((frame.date>=pd.Timestamp("2024-01-01"))&
                     (frame.date<pd.Timestamp("2025-01-01"))).to_numpy()
    model=algorithm("logistic_weak")
    model.fit(np.vstack([features[train_mask],-features[train_mask]]),
              np.r_[y[train_mask],1-y[train_mask]])
    static_cal=symmetric_prediction(model,features[validation_mask])
    # Reconstruct frozen static policy on comparable 2026 rows, do not select new gate.
    def static_predict(test_x):
        raw=symmetric_prediction(model,test_x)
        return calibrate_prior(static_cal,y[validation_mask],raw)[0]
    for cutoff,cal_start,end in QUARTERS:
        train=(frame.date<pd.Timestamp(cal_start)).to_numpy()
        cal=((frame.date>=pd.Timestamp(cal_start))&
             (frame.date<pd.Timestamp(cutoff))).to_numpy()
        test=((frame.date>=pd.Timestamp(cutoff))&
              (frame.date<pd.Timestamp(end))).to_numpy()
        if min(train.sum(),cal.sum(),test.sum())<MIN_PRECAL_FIGHTS:
            raise ValueError("Quarter cohort too small: "+cutoff)
        train_days=frame.loc[train,"date"].dt.date.to_numpy()
        cal_days=frame.loc[cal,"date"].dt.date.to_numpy()
        test_days=frame.loc[test,"date"].dt.date.to_numpy()
        validate_temporal(train_days,cal_days,test_days,cal_start,cutoff)
        fits={}
        candidate_raw={}
        candidate_metrics={}
        candidates_pred={}
        for name in FAMILIES:
            fitted=make_candidate(name)
            fitted.fit(np.vstack([features[train],-features[train]]),
                       np.r_[y[train],1-y[train]])
            prior=symmetric_prediction(fitted,features[cal])
            raw=symmetric_prediction(fitted,features[test])
            # Prior quarter performance determines next quarter choice.
            candidate_metrics[name]=score(prior,y[cal])["brier"]
            candidates_pred[name],slope=calibrate_prior(prior,y[cal],raw)
            traces[name].extend(candidates_pred[name].tolist())
            fits[name]={"preCalBrier":float(candidate_metrics[name]),
                        "calibrationSlope":slope}
        chosen=min(FAMILIES,key=lambda name:(candidate_metrics[name],name))
        predictions=candidates_pred[chosen]
        baseline=static_predict(features[test])
        for idx,prob,base in zip(np.where(test)[0],predictions,baseline):
            row=frame.iloc[int(idx)]
            rows.append({
              "fight_id":str(row.fight_id),"date":str(row.date.date()),
              "red":str(row.r_name),"blue":str(row.b_name),
              "redProbability":float(prob),"staticProbability":float(base),
              "eloProbability":float(row.p_elo32),
              "resultRed":int(row.winner),
              "family":chosen,
              "familySelectedUsing":"prior-quarter Brier only",
              "confidencePass":bool(max(prob,1-prob)>=SELECTION_THRESHOLD),
            })
        selection.append({
          "quarterStart":cutoff,"calibrationStart":cal_start,
          "quarterEndExclusive":end,"trainingCount":int(train.sum()),
          "calibrationCount":int(cal.sum()),
          "evaluatedCount":int(test.sum()),
          "selectedFamily":chosen,
          "candidatePriorQuarterBrier":fits,
          "rollingAccuracy":score(predictions,y[test])["accuracy"],
          "rollingSelective":score(predictions,y[test],SELECTION_THRESHOLD),
          "staticAccuracy":score(baseline,y[test])["accuracy"],
          "eloAccuracy":score(frame.loc[test,"p_elo32"].to_numpy(),y[test])["accuracy"],
        })
    if not rows:raise ValueError("No 2026 prequential predictions")
    if len({r["fight_id"] for r in rows})!=len(rows):
        raise ValueError("Duplicate 2026 prediction records")
    observed=[r["resultRed"] for r in rows]
    rolling=[r["redProbability"] for r in rows]
    old=[r["staticProbability"] for r in rows]
    elo=[r["eloProbability"] for r in rows]
    date=[r["date"] for r in rows]
    if len(rolling)!=sum(x["evaluatedCount"] for x in selection):
        raise ValueError("Quarter coverage inconsistency")
    cohort={
      "rolling":score(rolling,observed),
      "rollingSelective75":score(rolling,observed,SELECTION_THRESHOLD),
      "staticFrozen2024":score(old,observed),
      "staticSelective75":score(old,observed,SELECTION_THRESHOLD),
      "elo32":score(elo,observed),
    }
    # The raw family comparators are NOT selected by 2026 performance.
    comparisons={}
    for family in FAMILIES:
        comps=traces[family]
        if len(comps)!=len(observed):raise ValueError("Family timeline misaligned")
        comparisons[family]=score(comps,observed)
    advantage=cohort["rolling"]["accuracy"]-cohort["staticFrozen2024"]["accuracy"]
    prospectiveLabel="2026 retrospective DEVELOPMENT replay, NOT sealed validation"
    return {
      "schema":"JSA_ROLLING_2026_V1",
      "period":prospectiveLabel,
      "eventCount":len(set(date)),
      "fightCount":len(rows),
      "trainingPolicy":"Quarterly: train before previous quarter, choose and calibrate on previous quarter; evaluate next quarter",
      "trainingFeatureOrigin":"Pinned upstream UFCash date-batched pre-fight features; independent as-of audits still required",
      "modelFamilies":list(FAMILIES),
      "fixedThreshold":SELECTION_THRESHOLD,
      "prospectiveValidated":False,
      "testPeriodTuned":False,
      "developmentPeriodAlreadyExamined":True,
      "quarterly":selection,
      "matchedCohort":cohort,
      "candidateResults2026_DIAGNOSTIC_ONLY":comparisons,
      "rollingMinusStaticAccuracyPp":round(100*advantage,4),
      "rollingMinusStaticAccuracyCI95Pp":[round(100*z,3) for z in paired_event_bootstrap(rolling,old,observed,date)],
      "confidenceRisk": {
        "2026Ece":cohort["rolling"]["ece_10bins"],
        "2026CalibrationSampleSize":len(rows),
        "note":"Paired event-clustered bootstrap is exploratory. Historical source may contain retrospective revisions."
      },
      "eligibleFuture2026Policy":"Do not select a champion based on these 2026 test results; lock policy before newly occurring events",
      "claimed99_9":False,"verifiedBettingProfit":False,
      "predictions":rows
    }


def main():
    import pandas as pd
    root=Path(__file__).resolve().parents[1]
    path=root/"ufcash"/"data"/"processed"/"features.parquet"
    frame=pd.read_parquet(path)
    frame["date"]=pd.to_datetime(frame["date"],errors="raise")
    eligibility=(frame.winner.isin([0,1]))&(frame.r_n_fights>=3)&(frame.b_n_fights>=3)
    eligibility&=(frame.date>=pd.Timestamp("2012-01-01"))&(frame.date<pd.Timestamp("2026-11-19"))
    hist=frame.loc[eligibility].sort_values(["date","fight_id"]).copy()
    report=evaluate(hist)
    out=root/"results"
    out.mkdir(exist_ok=True)
    selected={k:v for k,v in report.items() if k!="predictions"}
    (out/"rolling_2026_summary.json").write_text(json.dumps(selected,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    (out/"rolling_2026_predictions.json").write_text(json.dumps(report["predictions"],indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({
        "eventDays":report["eventCount"],"fights":report["fightCount"],
        "rolling":report["matchedCohort"]["rolling"],
        "static":report["matchedCohort"]["staticFrozen2024"],
        "elo":report["matchedCohort"]["elo32"],
        "rollingHighConfidence":report["matchedCohort"]["rollingSelective75"],
        "changePp":report["rollingMinusStaticAccuracyPp"],
        "pairedCI95Pp":report["rollingMinusStaticAccuracyCI95Pp"],
        "quarters":[(x["quarterStart"],x["selectedFamily"]) for x in report["quarterly"]],
        "warning":"RETROSPECTIVE development replay, not untouched or proven betting profits"
    },indent=2,allow_nan=False))


if __name__=="__main__":
    main()
