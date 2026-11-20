#!/usr/bin/env python3
"""J$A Accuracy Frontier v2: precommitted 2025 selection, 2026 retrospective audit.

STRICT ORDER:
  Fit: 2012-2024, except frozen 2012-2023 comparator.
  Calibration only: Jan-Jun 2025.
  Family selection + confidence gate only: Jul-Dec 2025.
  Historical diagnostic evaluation only: Jan-18 Nov 2026.
2026 already examined in prior project stages: NOT a fresh prospective holdout.
All inputs date-batched UFCStats-derived prior-fight stats and past rating
features. Do not use odds, fighter names, outcomes or future source revisions
as model inputs. No wagers or ROI.
"""
from __future__ import annotations
import datetime as dt
import json
import math
from pathlib import Path

from scripts.precision_lab import read_input, algorithm, symmetric_prediction, summary
from scripts.rolling_2026 import make_candidate, ece, paired_event_bootstrap

SEED=20261120
TRAIN_2025="2025-01-01"
CAL_END="2025-07-01"
TEST_START="2026-01-01"
HIST_END="2026-11-19"
CONFIDENCE_GRID=(.5,.6,.65,.7,.75,.8,.85)
MIN_SELECTED_VALIDATION=35
MIN_COVERAGE_VALIDATION=.20
CANDIDATES=("frozen_v1","recent_logistic","time_decay_logistic","nonlinear_ensemble","elo_blend")
INTERACTIONS=(
    ("c_sdiff","c_td15"),
    ("c_ctrl","c_sdiff"),
    ("win_rate","p_elo32"),
    ("c_tddef","c_td15"),
    ("e_adj_net","p_glicko"),
    ("fights_2y","days_since"),
)


def interactions(x, names):
    """Corner-swap antisymmetry: f(-x) = -f(x); no even-order interactions."""
    import numpy as np
    if len(set(names))!=len(names):
        raise ValueError("Duplicate source feature names")
    extra=[]
    for a,b in INTERACTIONS:
        if a not in names or b not in names:
            raise ValueError("Interaction requires upstream features: "+a+" / "+b)
        i,j=names.index(a),names.index(b)
        extra.append(np.clip(x[:,i]*np.abs(x[:,j]),-150,150))
    return np.column_stack([x]+extra)


def time_decay(dates, asof, half_life_years=4.0):
    import numpy as np
    import pandas as pd
    dates=pd.to_datetime(dates)
    t=pd.Timestamp(asof)
    age=(t-dates).dt.days.to_numpy(dtype=float)
    if (age<0).any():
        raise ValueError("Training rows include future dates")
    w=np.power(.5,age/(365.25*half_life_years))
    return np.clip(w,.12,1.0)


def mirrored_fit(model,x,y,weights=None):
    import numpy as np
    assert len(x)==len(y) and len(y)>0
    xx=np.vstack([x,-x]);yy=np.r_[y,1-y]
    if weights is not None:
        w=np.r_[weights,weights]
        if hasattr(model,"named_steps"):
            model.fit(xx,yy,logisticregression__sample_weight=w)
        else:
            model.fit(xx,yy,sample_weight=w)
    else:
        model.fit(xx,yy)
    return model


def symmetric_platt(p_cal,y_cal,p_new):
    """Model frozen before calibration. Symmetric logistic slope fitted on 2025 H1."""
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    def logit(p):
        p=np.clip(np.asarray(p,dtype=float),1e-4,1-1e-4)
        return np.log(p/(1-p)).reshape(-1,1)
    if len(p_cal)<100 or len(y_cal)!=len(p_cal):
        raise ValueError("Missing sufficient 2025 H1 calibration rows")
    m=LogisticRegression(C=1.0,fit_intercept=False,max_iter=1000)
    m.fit(np.vstack([logit(p_cal),-logit(p_cal)]),
          np.r_[y_cal,1-y_cal])
    value=m.predict_proba(logit(p_new))[:,1]
    return value,float(m.coef_[0,0])


def choose_family(dev,truth):
    """Single family selected on 2025 H2 Brier ONLY; 2026 never used to choose."""
    keys=tuple(dev)
    if keys!=CANDIDATES:
        raise ValueError("Family selection contract changed")
    scores={}
    for key,p in dev.items():
        stat=summary(list(p),list(truth))
        scores[key]={"accuracy":stat["accuracy"],"brier":stat["brier"],
                     "logloss":stat["logloss"],"n":stat["selected"]}
    selected=min(CANDIDATES,key=lambda k:(scores[k]["brier"],CANDIDATES.index(k)))
    return selected,scores


def choose_gate(prob,y):
    """Select gate on 2025 H2, not 2026. Require useful minimum coverage."""
    candidates=[]
    for t in CONFIDENCE_GRID:
        s=summary(list(prob),list(y),t)
        if s["selected"]>=MIN_SELECTED_VALIDATION and s["coverage"]>=MIN_COVERAGE_VALIDATION:
            candidates.append((s["wilson95Lower"],s["coverage"],-t,t,s))
    if not candidates:
        raise ValueError("No threshold meets validation size and coverage requirements")
    win=max(candidates,key=lambda q:(q[0],q[1],q[2]))
    return win[3],win[4]


def calculate():
    import numpy as np
    import pandas as pd
    base=Path(__file__).resolve().parents[1]
    table=base/"ufcash"/"data"/"processed"/"features.parquet"
    if not table.exists():
        raise ValueError("Required upstream UFCash historical features missing")
    data=pd.read_parquet(table)
    data["date"]=pd.to_datetime(data["date"],errors="raise")
    eligible=(data.winner.isin([0,1])) & (data.r_n_fights>=3)&(data.b_n_fights>=3)
    eligible &= (data.date>=pd.Timestamp("2012-01-01")) & (data.date<pd.Timestamp(HIST_END))
    history=data.loc[eligible].sort_values(["date","fight_id"]).copy()
    if history.fight_id.duplicated().any():
        raise ValueError("Duplicate fights contaminate chronology")
    splits={
       "frozen_train": history.date<pd.Timestamp("2024-01-01"),
       "frozen_cal": (history.date>=pd.Timestamp("2024-01-01"))&(history.date<pd.Timestamp(TRAIN_2025)),
       "train":history.date<pd.Timestamp(TRAIN_2025),
       "cal":(history.date>=pd.Timestamp(TRAIN_2025))&(history.date<pd.Timestamp(CAL_END)),
       "dev":(history.date>=pd.Timestamp(CAL_END))&(history.date<pd.Timestamp(TEST_START)),
       "test":history.date>=pd.Timestamp(TEST_START),
    }
    frames={k:history.loc[v].copy() for k,v in splits.items()}
    sizes={k:len(v) for k,v in frames.items()}
    if sizes["frozen_train"]<2000 or sizes["train"]<2300 or min(sizes["frozen_cal"],sizes["cal"],sizes["dev"])<90 or sizes["test"]<200:
        raise ValueError("Historical window unexpectedly small: "+str(sizes))
    if not (frames["train"].date.max()<frames["cal"].date.min() and
       frames["cal"].date.max()<frames["dev"].date.min() and
       frames["dev"].date.max()<frames["test"].date.min()):
        raise ValueError("Chronological split integrity violated")
    xx={};yi={};schema=None
    for name,df in frames.items():
        xx[name],current=read_input(df)
        if schema is None:schema=current
        if current!=schema:raise ValueError("Source features differ by split")
        yi[name]=df.winner.astype(int).to_numpy()
    xi={key:interactions(value,schema) for key,value in xx.items()}
    # Same-source Elo has only pre-event form. This is a challenger input, not a bookmaker line.
    elo={key:frames[key]["p_elo32"].clip(.001,.999).to_numpy(dtype=float) for key in frames}

    # 2012-2023 fixed historical benchmark; 2024 calibration used to freeze it.
    frozen=mirrored_fit(algorithm("logistic_weak"),xx["frozen_train"],yi["frozen_train"])
    f2024=symmetric_prediction(frozen,xx["frozen_cal"])
    frozen_cal={}
    for k in ("dev","test"):
        frozen_cal[k],_ = symmetric_platt(f2024,yi["frozen_cal"],symmetric_prediction(frozen,xx[k]))

    # Four independent 2012-2024 base learners, plus temporal-decay regularization.
    weights=time_decay(frames["train"].date,TRAIN_2025)
    f={}
    f["recent_logistic"]=mirrored_fit(algorithm("logistic_weak"),xi["train"],yi["train"])
    f["time_decay_logistic"]=mirrored_fit(algorithm("logistic_weak"),xi["train"],yi["train"],weights)
    f["hist_boost"]=mirrored_fit(algorithm("hist_boost"),xi["train"],yi["train"])
    f["xgboost"]=mirrored_fit(make_candidate("xgboost"),xi["train"],yi["train"])
    f["catboost"]=mirrored_fit(make_candidate("catboost"),xi["train"],yi["train"])
    raw={}
    for name,model in f.items():
        raw[name]={key:symmetric_prediction(model,xi[key])
                   for key in ("cal","dev","test")}
    def assembled(key):
        return {
          "frozen_v1":frozen_cal[key],
          "recent_logistic":raw["recent_logistic"][key],
          "time_decay_logistic":raw["time_decay_logistic"][key],
          "nonlinear_ensemble":(
             .4*raw["recent_logistic"][key]+
             .2*raw["hist_boost"][key]+
             .2*raw["xgboost"][key]+
             .2*raw["catboost"][key]),
          "elo_blend":(.80*raw["recent_logistic"][key]+.20*elo[key]),
        }
    def raw_assembled_cal():
        return {
          "recent_logistic":raw["recent_logistic"]["cal"],
          "time_decay_logistic":raw["time_decay_logistic"]["cal"],
          "nonlinear_ensemble":(
              .4*raw["recent_logistic"]["cal"]+
              .2*raw["hist_boost"]["cal"]+
              .2*raw["xgboost"]["cal"]+
              .2*raw["catboost"]["cal"]),
          "elo_blend":(.80*raw["recent_logistic"]["cal"]+.20*elo["cal"]),
        }
    calib=raw_assembled_cal()
    devraw=assembled("dev");testraw=assembled("test")
    predictions={"dev":{"frozen_v1":frozen_cal["dev"]},
                 "test":{"frozen_v1":frozen_cal["test"]}}
    slopes={}
    for name in CANDIDATES[1:]:
        # No 2025 H2 or 2026 outcomes in calibration.
        devpred,slope=symmetric_platt(calib[name],yi["cal"],devraw[name])
        testpred,_=symmetric_platt(calib[name],yi["cal"],testraw[name])
        predictions["dev"][name]=devpred
        predictions["test"][name]=testpred
        slopes[name]=slope
    chosen,devscores=choose_family(predictions["dev"],yi["dev"])
    threshold,validationGate=choose_gate(predictions["dev"][chosen],yi["dev"])
    out={}
    for family in CANDIDATES:
        probs=predictions["test"][family]
        score=summary(probs.tolist(),yi["test"].tolist())
        score["ece10"]=ece(probs,yi["test"])
        score["selectedAtFrozen75"]=summary(probs.tolist(),yi["test"].tolist(),.75)
        out[family]=score
    selected=predictions["test"][chosen]
    selectedStats=summary(selected.tolist(),yi["test"].tolist(),threshold)
    fixed75=summary(selected.tolist(),yi["test"].tolist(),.75)
    baseline=summary(elo["test"].tolist(),yi["test"].tolist())
    old=frozen_cal["test"]
    dates=frames["test"].date.dt.date.to_numpy()
    interval=paired_event_bootstrap(selected,old,yi["test"],dates,reps=800)
    per_quarter={}
    for q in (1,2,3,4):
        ix=(frames["test"].date.dt.quarter.to_numpy()==q)
        if not ix.any():continue
        values=selected[ix]
        labels=yi["test"][ix]
        per_quarter["Q"+str(q)]={
         "n":int(sum(ix)),
         "accuracy":summary(values.tolist(),labels.tolist())["accuracy"],
         "chosenSelective":summary(values.tolist(),labels.tolist(),threshold),
         "brier":summary(values.tolist(),labels.tolist())["brier"]
        }
    # Upcoming forecasts: same versioned model frozen before 2026; no 2026 outcome used.
    upcoming=data[(data.outcome=="UPCOMING")&
                  (data.date==pd.Timestamp("2026-11-21"))].sort_values("card_pos")
    if len(upcoming)!=7:
        raise ValueError("Upcoming seven-bout source changed; no predictions published")
    xu,names=read_input(upcoming)
    if names!=schema:raise ValueError("Upcoming feature schema changed")
    xui=interactions(xu,names)
    pu={}
    pu["frozen_v1"]=symmetric_platt(f2024,yi["frozen_cal"],
                       symmetric_prediction(frozen,xu))[0]
    raw_future={name:symmetric_prediction(model,xui) for name,model in f.items()}
    future={
      "recent_logistic":raw_future["recent_logistic"],
      "time_decay_logistic":raw_future["time_decay_logistic"],
      "nonlinear_ensemble":(
         .4*raw_future["recent_logistic"]+
         .2*raw_future["hist_boost"]+
         .2*raw_future["xgboost"]+
         .2*raw_future["catboost"]),
      "elo_blend":(.8*raw_future["recent_logistic"]+
                    .2*upcoming.p_elo32.clip(.001,.999).to_numpy(dtype=float)),
    }
    for name in CANDIDATES[1:]:
        pu[name],_=symmetric_platt(calib[name],yi["cal"],future[name])
    forecasts=[]
    for i,row in enumerate(upcoming.itertuples(index=False)):
        eligibility=bool(row.r_n_fights>=3 and row.b_n_fights>=3)
        pr=float(pu[chosen][i])
        forecasts.append({
          "fighterA":str(row.r_name),"fighterB":str(row.b_name),
          "redProbability":round(pr,6) if eligibility else None,
          "passesValidationLockedGate":bool(eligibility and max(pr,1-pr)>=threshold),
          "sufficientPriorHistory":eligibility,
          "outcome":None,"betPlaced":False,
        })
    report={
      "schema":"JSA_ACCURACY_FRONTIER_2026_V1",
      "timestampPolicy":"Source study; date-scoped and frozen before event",
      "evaluationClass":"2026 ALREADY EXAMINED retrospective development, not untouched",
      "windows":{"train":"2012-2024","calibration":"2025-H1",
                 "familySelection":"2025-H2","test":"2026-01-01 through 2026-11-18"},
      "sizes":sizes,"families":list(CANDIDATES),
      "upstreamFeatureCount":len(schema),"interactionCount":len(INTERACTIONS),
      "symmetricSwapInvariant":True,
      "calibration":"2025 H1 independent symmetric Platt",
      "familyPickedUsing":"2025 H2 minimum Brier only, 2026 outcomes never used",
      "selectedFamily":chosen,"selectionValidationMetrics":devscores,
      "calibrationSlopes":slopes,
      "gateSelection":"2025 H2 Wilson lower, >=35 accepted and >=20% covered",
      "selectedConfidenceGate":threshold,"gateValidation":validationGate,
      "full2026FamilyDIAGNOSTICS_NotForSelectingFamily":out,
      "chosenFull2026":out[chosen],
      "chosenSelective2026":selectedStats,
      "chosenSelectedAt75":fixed75,
      "frozenFull2026":out["frozen_v1"],
      "matchedElo2026":baseline,
      "pairedEventBootstrapChosenMinusFrozenAccuracyCI95pp":[round(100*v,3) for v in interval],
      "accuracyChangePp":round(100*(out[chosen]["accuracy"]-out["frozen_v1"]["accuracy"]),4),
      "perQuarter":per_quarter,
      "forecast21November":forecasts,
      "prospectiveWinningEdgeVerified":False,"accuracy99_9Verified":False,"realBetsPlaced":False,
      "risk":"2026 already viewed; hypotheses/data source can have revisions; no independent historic as-of audit. No verified executable odds or profit.",
    }
    # Additional audit-only per-fight evidence. Historical scores and choice are
    # unchanged. Source fighter information is public; no betting/bankroll data.
    cases = {
      "schema":"JSA_FRONTIER_CASES_V1",
      "modelSelectedUsing":"2025 H2 only",
      "model":chosen,
      "scope":"2025 H2 selection and already-inspected 2026 DEVELOPMENT",
      "fighterVariables":"Prior-to-fight features from UFCash, potentially retrospectively revised",
      "selection2025":[],
      "development2026":[],
    }
    for split, key in (("dev","selection2025"),("test","development2026")):
        table=frames[split]
        for i, row in enumerate(table.itertuples(index=False)):
            def finite_or_none(v):
                try:
                    n=float(v)
                    return n if math.isfinite(n) else None
                except (TypeError,ValueError):
                    return None
            probs={name:round(float(predictions[split][name][i]),9) for name in CANDIDATES}
            cases[key].append({
              "id":str(row.fight_id),
              "date":str(row.date.date()),
              "winnerA":int(row.winner),
              "fighters":[str(row.r_name),str(row.b_name)],
              "probabilities":probs,
              "fights":[int(row.r_n_fights),int(row.b_n_fights)],
              "daysSince":[finite_or_none(row.r_days_since),finite_or_none(row.b_days_since)],
              "elo32":round(float(row.p_elo32),9),
            })
    if len(cases["selection2025"])!=sizes["dev"] or len(cases["development2026"])!=sizes["test"]:
        raise ValueError("Frontier audit case count mismatch")
    if len({x["id"] for x in cases["development2026"]})!=sizes["test"]:
        raise ValueError("Duplicate frontier case identifier")
    case_path=Path(__file__).resolve().parents[1]/"results"/"frontier_cases.json"
    case_path.write_text(json.dumps(cases,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")

    path=Path(__file__).resolve().parents[1]/"results"/"accuracy_frontier_2026.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({
      "chosenFrom2025":chosen,"gateFrom2025":threshold,
      "testCount":sizes["test"],
      "frozenAccuracy":out["frozen_v1"]["accuracy"],
      "chosenAccuracy":out[chosen]["accuracy"],
      "selectedAccuracy":selectedStats["accuracy"],
      "selectedCoverage":selectedStats["coverage"],
      "accuracyGainPp":report["accuracyChangePp"],
      "challengerBrier":out[chosen]["brier"],
      "frozenBrier":out["frozen_v1"]["brier"],
      "forecastCount":len(forecasts),
      "note":"2026 known development data; cannot call prospective/untouched"
    },indent=2,allow_nan=False))
    return report


if __name__=="__main__":
    calculate()
