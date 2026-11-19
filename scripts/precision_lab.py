#!/usr/bin/env python3
"""J$A precision lab v1: an independent, odds-free UFC predictor.

2012-2023: train fixed candidate models; 2024: choose model and calibrate/lock
selective confidence policy; 2025-2026: strictly unseen test. No test-informed
hyperparameters. Only pre-event rolling UFC fighter stats and rating inputs.
No winner/fighter identity/odds or post-fight stats are model features.

Upstream UFCash generates date-batched features from strictly prior fights.
We intentionally exclude the imputed physical data (its missingness can encode
future tenure), the market-derived fighter features, prices, and corner flags.
The data source still needs independent feature-time auditing before claims.
"""
import json
import math
import sys
from pathlib import Path

FEATURES = (
    "n_fights", "wins", "losses", "win_rate", "last3_wr", "last5_wr",
    "win_streak", "lose_streak", "fights_2y", "days_since", "total_min",
    "avg_min", "finish_win_rate", "finished_rate", "ko_loss_rate",
    "n_stat_fights", "c_slpm", "c_sapm", "c_sdiff", "c_sacc", "c_sdef",
    "c_td15", "c_td_abs15", "c_tdacc", "c_tddef", "c_sub15",
    "c_ctrl", "c_ctrl_abs", "c_kd15", "c_head_pm", "c_head_abs_pm",
    "c_str_share", "e_slpm", "e_sapm", "e_sdiff", "e_td15",
    "e_ctrl", "e_ctrl_abs", "e_adj_net", "c_adj_net", "r1_diff_pm",
    "late_diff_pm", "fade", "opp_elo_mean", "beaten_elo_max",
)
RATINGS = ("p_elo32", "p_elo64", "p_elo_str", "p_elo_ctrl", "p_glicko")
LOG_FIELDS = frozenset((
    "n_fights","wins","losses","win_streak","lose_streak","fights_2y",
    "days_since","total_min","avg_min","n_stat_fights","c_td15",
    "c_td_abs15","c_sub15","c_kd15","e_td15","c_head_pm",
    "c_head_abs_pm","beaten_elo_max"
))
THRESHOLDS = (0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.85,0.90,0.95)


def wilson_lower(wins, n, z=1.959963984540054):
    if n==0: return None
    p=wins/n
    d=1+z*z/n
    return max(0.0,(p+z*z/(2*n)-z*math.sqrt((p*(1-p)+z*z/(4*n))/n))/d)


def summary(probabilities, outcomes, threshold=0.5):
    """Evaluation function, no tuning. Callable with plain Python lists."""
    if len(probabilities)!=len(outcomes):
        raise ValueError("Probabilities and outcomes length mismatch")
    accepted = [(float(p),int(y)) for p,y in zip(probabilities,outcomes)
                if max(float(p),1-float(p))>=threshold]
    for p,y in zip(probabilities,outcomes):
        if not (math.isfinite(float(p)) and 0<float(p)<1 and int(y) in (0,1)):
            raise ValueError("Only finite probabilities and binary outcomes allowed")
    n=len(accepted)
    correct=sum((p>=0.5)==bool(y) for p,y in accepted)
    out={
        "selected":n,"eligible":len(probabilities),
        "coverage":n/len(probabilities) if probabilities else None,
        "correct":correct,"accuracy":correct/n if n else None,
        "wilson95Lower":wilson_lower(correct,n),
        "brier":sum((p-y)**2 for p,y in accepted)/n if n else None,
        "logloss":-sum(y*math.log(max(1e-12,p))+(1-y)*math.log(max(1e-12,1-p)) for p,y in accepted)/n if n else None,
    }
    return out


def lock_policy(validation_probabilities, validation_outcomes):
    """Choose confidence gate on validation ONLY; lower bound and coverage."""
    candidate=[]
    for threshold in THRESHOLDS:
        stat=summary(validation_probabilities,validation_outcomes,threshold)
        if stat["selected"]>=25 and stat["coverage"]>=0.08:
            candidate.append((stat["wilson95Lower"],stat["coverage"],threshold,stat))
    if not candidate:
        return {"threshold":1.0,"validation":None,"reason":"No predeclared gate has >=25 accepted validation fights and >=8% coverage"}
    _,_,threshold,stat=max(candidate,key=lambda x:(x[0],x[1]))
    return {"threshold":threshold,"validation":stat,"reason":"Maximum validation-only 95% Wilson lower bound with minimum accepted sample and coverage"}


def read_input(frame):
    """Explicit allowlist: no odds/market, winner, IDs, future attributes."""
    import numpy as np
    import pandas as pd
    missing=[f for f in FEATURES if "r_"+f not in frame or "b_"+f not in frame]
    usable=[f for f in FEATURES if f not in missing]
    missing_rating=[k for k in RATINGS if k not in frame]
    if len(usable)<28 or len(missing_rating)>0:
        raise ValueError("Upstream feature contract changed: missing "+str(missing+missing_rating))
    matrix=[]
    for name in usable:
        a=pd.to_numeric(frame["r_"+name],errors="coerce").to_numpy(dtype=float)
        b=pd.to_numeric(frame["b_"+name],errors="coerce").to_numpy(dtype=float)
        # No use of future missingness indicators; non-physical prior stats only.
        a=np.nan_to_num(a,nan=0.0,posinf=0.0,neginf=0.0)
        b=np.nan_to_num(b,nan=0.0,posinf=0.0,neginf=0.0)
        a=np.clip(a,-1e5,1e5);b=np.clip(b,-1e5,1e5)
        if name in LOG_FIELDS:
            a=np.sign(a)*np.log1p(abs(a))
            b=np.sign(b)*np.log1p(abs(b))
        matrix.append(np.clip(a-b,-200.0,200.0))
    for name in RATINGS:
        p=pd.to_numeric(frame[name],errors="coerce").to_numpy(dtype=float)
        p=np.clip(np.nan_to_num(p,nan=.5,posinf=.5,neginf=.5),0.001,0.999)
        matrix.append(np.log(p/(1-p)))
    return np.column_stack(matrix),usable+list(RATINGS)


def algorithm(name):
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import HistGradientBoostingClassifier
    if name=="logistic_weak":
        return make_pipeline(StandardScaler(),LogisticRegression(C=.08,fit_intercept=False,max_iter=1200))
    if name=="logistic_regular":
        return make_pipeline(StandardScaler(),LogisticRegression(C=.6,fit_intercept=False,max_iter=1200))
    if name=="hist_boost":
        return HistGradientBoostingClassifier(max_iter=180,max_leaf_nodes=9,max_depth=3,
                   min_samples_leaf=45,learning_rate=.045,l2_regularization=2,
                   early_stopping=False,random_state=2026)
    raise ValueError("Unknown fixed candidate "+name)


def symmetric_prediction(model, x):
    import numpy as np
    p=model.predict_proba(x)[:,1]
    q=model.predict_proba(-x)[:,1]
    return np.clip((p+1-q)/2,1e-4,1-1e-4)


def main():
    import numpy as np
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import brier_score_loss
    root=Path(__file__).resolve().parents[1]
    source=root/"ufcash"/"data"/"processed"/"features.parquet"
    if not source.is_file():
        raise SystemExit("UFCash pre-fight features missing: setup required")
    frame=pd.read_parquet(source)
    frame["date"]=pd.to_datetime(frame["date"],errors="raise")
    required=("winner","date","r_n_fights","b_n_fights","outcome","r_name","b_name")
    if any(k not in frame for k in required):
        raise SystemExit("Upstream feature table lacks required columns")
    # All pre-fight features were generated before the same-day result update.
    eligible=(frame["r_n_fights"]>=3)&(frame["b_n_fights"]>=3)
    valid=(frame.winner.isin([0,1]))&eligible&(frame.date>=pd.Timestamp("2012-01-01"))&(frame.date<pd.Timestamp("2026-11-19"))
    past=frame.loc[valid].copy()
    if past["fight_id"].duplicated().any():
        raise SystemExit("Duplicate historic fight IDs")
    periods={
      "train":past.date<pd.Timestamp("2024-01-01"),
      "validation":(past.date>=pd.Timestamp("2024-01-01"))&(past.date<pd.Timestamp("2025-01-01")),
      "test":past.date>=pd.Timestamp("2025-01-01")
    }
    sample={key:past.loc[mask].copy() for key,mask in periods.items()}
    if min(map(len,sample.values()))<100:
        raise SystemExit("Insufficient chronological data in one or more folds")
    x={};y={};schema=None
    for group,subset in sample.items():
        x[group],names=read_input(subset)
        if schema is None:schema=names
        elif names!=schema:raise SystemExit("Feature contract mismatch across folds")
        y[group]=subset.winner.astype(int).to_numpy()
    candidates={}
    fitted={}
    for name in ("logistic_weak","logistic_regular","hist_boost"):
        model=algorithm(name)
        model.fit(np.vstack([x["train"],-x["train"]]),np.r_[y["train"],1-y["train"]])
        val=symmetric_prediction(model,x["validation"])
        score=summary(val,y["validation"].tolist())
        candidates[name]={"validationBrier":score["brier"],"validationAccuracy":score["accuracy"]}
        fitted[name]=model
    selected=min(candidates,key=lambda k:(candidates[k]["validationBrier"],k))
    model=fitted[selected]
    val_raw=symmetric_prediction(model,x["validation"])
    # Platt slope calibrated on 2024 only, no intercept to preserve red/blue symmetry.
    logits=np.log(val_raw/(1-val_raw)).reshape(-1,1)
    calibrator=LogisticRegression(C=1.0,fit_intercept=False,max_iter=1000)
    calibrator.fit(np.vstack([logits,-logits]),np.r_[y["validation"],1-y["validation"]])
    def calibrate(raw):
        raw=np.clip(raw,1e-4,1-1e-4)
        v=np.log(raw/(1-raw)).reshape(-1,1)
        return calibrator.predict_proba(v)[:,1]
    val_p=calibrate(val_raw)
    policy=lock_policy(val_p.tolist(),y["validation"].tolist())
    test_raw=symmetric_prediction(model,x["test"])
    test_p=calibrate(test_raw)
    gate=policy["threshold"]
    holdout=summary(test_p.tolist(),y["test"].tolist())
    selective=summary(test_p.tolist(),y["test"].tolist(),gate)
    uncalibrated=summary(test_raw.tolist(),y["test"].tolist())
    ratings=sample["test"]["p_elo32"].clip(1e-4,1-1e-4).to_numpy(dtype=float)
    baseline=summary(ratings.tolist(),y["test"].tolist())
    per_year={}
    for year in (2025,2026):
        mask=sample["test"].date.dt.year.to_numpy()==year
        per_year[str(year)]=summary(test_p[mask].tolist(),y["test"][mask].tolist(),gate)
    curves=[dict(threshold=threshold,**summary(test_p.tolist(),y["test"].tolist(),threshold)) for threshold in THRESHOLDS]
    # Predictions: the frozen pre-2024 model + 2024 calibration only.
    next_fights=frame[(frame.outcome=="UPCOMING")&(frame.date==pd.Timestamp("2026-11-21"))].sort_values("card_pos")
    if len(next_fights)!=7:
        raise SystemExit("Expected seven actual upcoming fights, refusing partial card")
    next_x,next_names=read_input(next_fights)
    if next_names!=schema:
        raise SystemExit("Future feature schema mismatch")
    upcoming=calibrate(symmetric_prediction(model,next_x))
    forecasts=[]
    for row,p in zip(next_fights.itertuples(index=False),upcoming):
        covered=bool(row.r_n_fights>=3 and row.b_n_fights>=3)
        forecasts.append({
          "red":str(row.r_name),"blue":str(row.b_name),
          "probRed":round(float(p),6) if covered else None,
          "minPriorFightHistory":int(min(row.r_n_fights,row.b_n_fights)),
          "passesFrozenConfidenceGate":bool(covered and max(float(p),1-float(p))>=gate),
          "model":"frozen training through 2023, calibrated and gate-locked on 2024",
          "verifiedBettingEdge":False
        })
    data={
       "schema":"JSA_PRECISION_LAB_V1","eventDate":"2026-11-21",
       "training":"2012-2023", "validation":"2024 only", "lockedUnseenTest":"2025 through 2026-11-18",
       "source":"UFCash generated pre-fight feature table, NO market odds or imputed physical attributes",
       "noPostOutcomeFeatures":True,"sameDayInputRule":"Upstream features are computed from strictly earlier event dates",
       "eligibility":"both fighters at least 3 completed prior UFC fights",
       "featureNames":schema,"trainingCount":len(sample["train"]),
       "validationCount":len(sample["validation"]),"testCount":len(sample["test"]),
       "candidateValidationOnly":candidates,"chosenCandidate":selected,
       "calibration":"one symmetric Platt slope fitted to 2024 only",
       "lockedPolicy":policy,"untouchedTest":holdout,
       "selectedTest":selective,"uncalibratedTest":uncalibrated,
       "matchedCohortElo32Test":baseline,
       "testByYearAtLockedThreshold":per_year,
       "postHocRiskCoverageDiagnosticNotForTuning":curves,
       "upcomingPredictions":forecasts,
       "claim99_9Achieved":False,
       "warning":"Retrospective held-out evaluation, not independent prospective verification. High selected accuracy with tiny coverage is not a 99.9% claim. No market odds in training, calibration or inference; no demonstrated betting profit."
    }
    out=root/"results"/"precision_lab.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(data,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({"candidate":selected,"train":len(sample["train"]),"validation":len(sample["validation"]),
       "test":len(sample["test"]),"fullAccuracy":holdout["accuracy"],"eloMatchedAccuracy":baseline["accuracy"],
       "selectedAccuracy":selective["accuracy"],"selectedCoverage":selective["coverage"],
       "lockedThreshold":gate,"upcomingForecasts":len(forecasts)},indent=2))


if __name__=="__main__":
    main()
