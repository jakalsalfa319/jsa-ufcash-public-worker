#!/usr/bin/env python3
"""J$A Specialist Lab v3: regularized *residual* experts on frozen v2 probabilities.

The 2025 H2 coaching set is split chronologically into Q3 fit and Q4
development check; if the fixed check fails, baseline stays selected. Final
residual coefficients are fit only to 2025 H2. 2026 is an already-inspected
retrospective DIAGNOSTIC cohort, not an untouched test, and no model is promoted
for real-money use on the strength of it.

This is intentionally a cheap no-API experiment using previously fitted
models' pre-fight probabilities plus past style / experience data. No source
prices, fight outcomes or post-bout features are inference inputs.
"""
from __future__ import annotations
import datetime as dt
import json
import math
from pathlib import Path

import numpy as np
from scripts.precision_lab import summary
from scripts.rolling_2026 import ece, paired_event_bootstrap

BASE="nonlinear_ensemble"
SOURCE_SCHEMA="JSA_FRONTIER_CASES_V1"
L2=0.12                  # Frozen before examining new results.
MIN_Q3=35
MIN_Q4=35
MIN_VALIDATION_BRIER_GAIN=.001
MAX_VALIDATION_ACCURACY_DROP=.02
SELECTIVE_THRESHOLD=.65 # Existing v2 2025-locked threshold. Never re-optimize on 2026.
NAMES=("expert_recent","expert_decay","expert_frozen","experience_gap",
       "layoff_gap","striking_gap","wrestling_gap","defense_gap","control_gap",
       "style_mismatch")
SOURCE_FEATURES=("strikeDiff","takedowns15","takedownDefense","control")


def logit(p):
    p=np.clip(np.asarray(p,dtype=float),1e-5,1-1e-5)
    return np.log(p/(1-p))


def sigmoid(v):
    v=np.asarray(v,dtype=float)
    return 1/(1+np.exp(-np.clip(v,-35,35)))


def finite_pair(row,name):
    values=row.get("preFightStyle",{}).get(name,[None,None])
    if len(values)!=2:
        raise ValueError("Missing pre-fight style pair: "+name)
    if any(v is None or not math.isfinite(float(v)) for v in values):
        return (0.,0.)
    return float(values[0]),float(values[1])


def meta_features(row):
    p=row["probabilities"]
    for k in (BASE,"recent_logistic","time_decay_logistic","frozen_v1"):
        if k not in p or not math.isfinite(float(p[k])) or not 0<float(p[k])<1:
            raise ValueError("Invalid fixed-model probability "+k)
    base=float(logit(p[BASE]))
    def gap(k):
        return float(np.clip(float(logit(p[k]))-base,-2.5,2.5))
    fights=row.get("fights",[])
    days=row.get("daysSince",[])
    if len(fights)!=2 or min(fights)<3:
        raise ValueError("History eligibility not met")
    if len(days)!=2:
        raise ValueError("Missing inactivity history")
    ex=np.clip(math.log1p(fights[0])-math.log1p(fights[1]),-2.,2.)
    la=0. if any(d is None or not math.isfinite(float(d)) or float(d)<0 for d in days) else float(
        np.clip(math.log1p(days[0])-math.log1p(days[1]),-3,3))
    strike=finite_pair(row,"strikeDiff")
    td=finite_pair(row,"takedowns15")
    defense=finite_pair(row,"takedownDefense")
    control=finite_pair(row,"control")
    st=float(np.tanh((strike[0]-strike[1])/3.))
    wr=float(np.tanh((td[0]-td[1])/3.))
    de=float(np.tanh((defense[0]-defense[1])/1.))
    co=float(np.tanh((control[0]-control[1])/3.))
    return np.array([gap("recent_logistic"),gap("time_decay_logistic"),gap("frozen_v1"),
                     ex,la,st,wr,de,co,st*abs(wr)],dtype=float)


def check_rows(rows,year):
    if len(rows)<60:raise ValueError("Insufficient source rows")
    seen=set()
    for r in rows:
        if r.get("id") in seen or not r.get("id"):
            raise ValueError("Missing/duplicate fighter bout identifier")
        seen.add(r["id"])
        date=dt.date.fromisoformat(r["date"])
        if date.year!=year:raise ValueError("Future/wrong-year score contamination")
        if r.get("winnerA") not in (0,1):
            raise ValueError("Incomplete historical outcome")
        if "preFightStyle" not in r:
            raise ValueError("Pre-fight style evidence absent")
        x=meta_features(r)
        if x.shape!=(len(NAMES),) or not np.all(np.isfinite(x)):
            raise ValueError("Invalid specialist feature vector")
    return rows


def matrix(rows):
    x=np.stack([meta_features(r) for r in rows])
    base=np.array([float(logit(r["probabilities"][BASE])) for r in rows])
    y=np.array([int(r["winnerA"]) for r in rows])
    return x,base,y


def fit_residual(rows,penalty=L2):
    """Prior-preserving logistic residual with analytic convex Newton steps.

    Offset logit(v2) is fixed, only 10 residual coefficients are estimated.
    Regularization shrinks all corrections toward zero, preserving v2 as prior.
    No intercept: when corners swap, all inputs flip and p->1-p exactly.
    """
    if penalty<=0 or len(rows)<MIN_Q3:
        raise ValueError("Too little prior evidence or invalid regularization")
    x,base,y=matrix(rows)
    w=np.zeros(x.shape[1])
    for _ in range(36):
        p=sigmoid(base+x@w)
        grad=(x.T@(p-y))/len(y)+penalty*w
        hess=(x.T*(p*(1-p)))@x/len(y)+penalty*np.eye(len(w))
        step=np.linalg.solve(hess,grad)
        # The regularized logistic objective is convex; backtracking
        # guards against extreme early Newton updates.
        def objective(coeff):
            z=base+x@coeff
            return np.mean(np.logaddexp(0,z)-y*z)+.5*penalty*(coeff@coeff)
        current=objective(w)
        scale=1.0
        while scale>1e-6 and objective(w-scale*step)>current:
            scale*=.5
        w-=scale*step
        if max(abs(scale*step))<1e-8:break
    if not np.all(np.isfinite(w)):raise ValueError("Nonfinite specialist coefficients")
    return w


def predict(rows,weights):
    x,base,_=matrix(rows)
    return sigmoid(base+x@weights)


def stats(rows,prob,threshold=.5):
    y=[int(r["winnerA"]) for r in rows]
    s=summary(prob.tolist(),y,threshold)
    if threshold==.5:
        s["ece10"]=ece(prob,np.array(y))
    return s


def experiment(data):
    if data.get("schema")!=SOURCE_SCHEMA or data.get("model")!=BASE:
        raise ValueError("Versioned source model mismatch")
    dev=sorted(check_rows(data["selection2025"],2025),key=lambda r:(r["date"],r["id"]))
    test=sorted(check_rows(data["development2026"],2026),key=lambda r:(r["date"],r["id"]))
    if len(dev)!=146 or len(test)!=266:
        raise ValueError("Model source cohort sizes changed")
    if any(not ("2025-07-01"<=r["date"]<"2026-01-01") for r in dev):
        raise ValueError("2025 audit data outside predeclared selection period")
    if any(not ("2026-01-01"<=r["date"]<"2026-11-19") for r in test):
        raise ValueError("2026 audit data outside predeclared retrospective period")
    q3=[r for r in dev if r["date"]<"2025-10-01"]
    q4=[r for r in dev if r["date"]>="2025-10-01"]
    if min(len(q3),len(q4))<min(MIN_Q3,MIN_Q4):
        raise ValueError("Cannot perform chronological 2025 Q3 to Q4 validation")
    w_initial=fit_residual(q3)
    q4_new=predict(q4,w_initial)
    q4_old=np.array([r["probabilities"][BASE] for r in q4])
    q4_scores={"candidate":stats(q4,q4_new),"baseline":stats(q4,q4_old)}
    viable=(q4_scores["candidate"]["brier"]<=
             q4_scores["baseline"]["brier"]-MIN_VALIDATION_BRIER_GAIN
         and q4_scores["candidate"]["accuracy"]>=
             q4_scores["baseline"]["accuracy"]-MAX_VALIDATION_ACCURACY_DROP)
    # Even a pass is research-only: 2025 originally influenced v2 selection.
    # 2026 labels NEVER decide whether to fit/enable this challenger.
    w_final=fit_residual(dev) if viable else np.zeros(len(NAMES))
    new=predict(test,w_final)
    old=np.array([r["probabilities"][BASE] for r in test])
    all_stats=stats(test,new);ref_stats=stats(test,old)
    difference=100*(all_stats["accuracy"]-ref_stats["accuracy"])
    dates=[r["date"] for r in test]
    ci=paired_event_bootstrap(new,old,
         np.array([r["winnerA"] for r in test]),dates,reps=800)
    by_quarter={}
    for q in ("Q1","Q2","Q3","Q4"):
        months={"Q1":(1,2,3),"Q2":(4,5,6),"Q3":(7,8,9),"Q4":(10,11,12)}[q]
        ix=[i for i,r in enumerate(test) if int(r["date"][5:7]) in months]
        group=[test[i] for i in ix]
        by_quarter[q]={"n":len(group),"candidate":stats(group,new[ix]),
            "baseline":stats(group,old[ix])}
    output={
      "schema":"JSA_SPECIALIST_LAB_V3",
      "evidence":"retrospective already-examined 2026; NOT prospective or independently sealed",
      "features":list(NAMES),"penaltyL2":L2,
      "source":"frozen Frontier v2 per-fight predictions plus prior-fight stats",
      "2025Q3_fitCount":len(q3),"2025Q4_developmentCount":len(q4),
      "2025Q4_development":q4_scores,
      "validationPolicy":"Require 0.001 absolute Brier improvement and no more than 2pp hit-rate loss in 2025 Q4",
      "validationPassed":viable,
      "candidateWeights":[round(float(v),9) for v in w_final],
      "2026Eligible":len(test),
      "2026Challenger":all_stats,"2026Baseline":ref_stats,
      "2026Selected65":stats(test,new,SELECTIVE_THRESHOLD),
      "2026BaselineSelected65":stats(test,old,SELECTIVE_THRESHOLD),
      "2026AccuracyDifferencePp":round(difference,4),
      "accuracyChangeBootstrapEvent95CIpp":[round(100*x,3) for x in ci],
      "quarterly":by_quarter,
      "selectedModelForLiveBetting":False,
      "probabilitiesUsedForAnyWagers":False,
      "accuracy99_9Proven":False,
      "futurePromotionCondition":"New truly prospective UFC events only. No promotion from inspected 2026 results.",
      "warning":"Sparsely sampled specialist residuals may overfit 2025 and degrade future accuracy. Historical dataset source revisions were not independently frozen."
    }
    if not viable:
        output["rejectionReason"]="2025 Q4 check failed. All reported 2026 challenger results are unchanged v2 baseline."
    return output


def main():
    root=Path(__file__).resolve().parents[1]
    obj=json.loads((root/"results/frontier_cases.json").read_text(encoding="utf-8"))
    out=experiment(obj)
    path=root/"results/specialist_lab_v3.json"
    path.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({
      "validationPassed":out["validationPassed"],
      "fit":out["2025Q3_fitCount"],"development":out["2025Q4_developmentCount"],
      "2026Baseline":out["2026Baseline"]["accuracy"],
      "2026Challenger":out["2026Challenger"]["accuracy"],
      "2026AccuracyGainPP":out["2026AccuracyDifferencePp"],
      "q4":out["quarterly"]["Q4"]["candidate"],
      "note":"retrospective research, no automatic model promotion"
    },indent=2))


if __name__=="__main__":
    main()
