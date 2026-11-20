#!/usr/bin/env python3
"""Independent J$A Frontier v2 risk and drift audit.

Reads immutable model predictions for July-Dec 2025 and Jan-Nov 2026.
ALL rules and minimum sample sizes are fixed in source. Policy selection uses
2025 H2 only. 2026 is already-examined retrospective DEVELOPMENT, not an
untouched holdout or a prospective proof of betting performance.

The probability model itself is NEVER retrained or modified by this module.
"""
from __future__ import annotations

import collections
import json
import math
from pathlib import Path

BASE_MODEL="nonlinear_ensemble"
CONFIDENCE_ONLY=.65
MIN_SELECTED_VALIDATION=30
MIN_VALIDATION_COVERAGE=.20
RULES=(
    {"id":"baseline_65","confidence":.65,"min_fights":3,
     "max_spread":None,"max_layoff_days":None,"require_same_side":False},
    {"id":"stronger_70_min5","confidence":.70,"min_fights":5,
     "max_spread":None,"max_layoff_days":None,"require_same_side":False},
    {"id":"consensus_65_spread15","confidence":.65,"min_fights":3,
     "max_spread":.15,"max_layoff_days":None,"require_same_side":True},
    {"id":"experience_65_spread18","confidence":.65,"min_fights":5,
     "max_spread":.18,"max_layoff_days":None,"require_same_side":True},
    {"id":"fresh_70_540days","confidence":.70,"min_fights":3,
     "max_spread":None,"max_layoff_days":540,"require_same_side":False},
)


def wilson_lower(wins,n,z=1.959963984540054):
    if n<=0:return None
    p=wins/n
    d=1+z*z/n
    return max(0.,(p+z*z/(2*n)-z*math.sqrt(
        (p*(1-p)+z*z/(4*n))/n))/d)


def validate(rows,tag,*,want=None):
    if not isinstance(rows,list) or (want is not None and len(rows)!=want):
        raise ValueError("Wrong cohort size: "+tag)
    ids=set()
    for row in rows:
        key=row.get("id")
        if not isinstance(key,str) or not key or key in ids:
            raise ValueError("Missing or duplicate fight ID "+tag)
        ids.add(key)
        if len(row.get("fighters",[]))!=2 or any(not str(x).strip() for x in row["fighters"]):
            raise ValueError("Invalid fighter pair")
        if row.get("winnerA") not in (0,1):
            raise ValueError("Invalid historical outcome")
        if not isinstance(row.get("date"),str) or not row["date"].startswith(tag):
            # Each cohort has its own fixed chronology; tag is a year prefix.
            raise ValueError("Wrong time period")
        probs=row.get("probabilities",{})
        for name in ("nonlinear_ensemble","recent_logistic","time_decay_logistic","frozen_v1"):
            p=probs.get(name)
            if not isinstance(p,(float,int)) or not math.isfinite(p) or not 0<p<1:
                raise ValueError("Missing/invalid model probability "+name)
        fights=row.get("fights",[])
        if len(fights)!=2 or any(type(x) is not int or x<3 for x in fights):
            raise ValueError("Invalid historical prior-fight count")
        days=row.get("daysSince",[])
        if len(days)!=2 or any(d is not None and (
           not isinstance(d,(int,float)) or not math.isfinite(d) or d<0) for d in days):
            raise ValueError("Invalid pre-fight layoff")
    return rows


def model_spread(row):
    values=[row["probabilities"][name] for name in
            ("nonlinear_ensemble","recent_logistic","time_decay_logistic")]
    return max(values)-min(values)


def flags(row):
    p=row["probabilities"][BASE_MODEL]
    layoff=[d for d in row["daysSince"] if d is not None]
    return {
      "borderline_probability":max(p,1-p)<.65,
      "limited_history":min(row["fights"])<5,
      "large_model_spread":model_spread(row)>.15,
      "long_layoff":bool(layoff) and max(layoff)>540,
      "different_favorite_than_old":(p>=.5)!=
                (row["probabilities"]["frozen_v1"]>=.5),
    }


def passes(row,rule):
    p=row["probabilities"][BASE_MODEL]
    if max(p,1-p)<rule["confidence"] or min(row["fights"])<rule["min_fights"]:
        return False
    if rule["max_spread"] is not None and model_spread(row)>rule["max_spread"]:
        return False
    if rule["require_same_side"] and any(
       (q>=.5)!=(p>=.5) for q in
       [row["probabilities"][x] for x in ("recent_logistic","time_decay_logistic")]):
        return False
    if rule["max_layoff_days"] is not None:
        if any(d is None or d>rule["max_layoff_days"] for d in row["daysSince"]):
            return False
    return True


def score(rows,rule):
    chosen=[x for x in rows if passes(x,rule)]
    n=len(chosen)
    correct=sum(int(
        (x["probabilities"][BASE_MODEL]>=.5)==bool(x["winnerA"])
    ) for x in chosen)
    return {
      "eligible":len(rows),"selected":n,"correct":correct,
      "coverage":n/len(rows) if rows else None,
      "accuracy":correct/n if n else None,
      "wilson95Lower":wilson_lower(correct,n),
      "brier":sum((x["probabilities"][BASE_MODEL]-x["winnerA"])**2
                  for x in chosen)/n if n else None,
      "frozenSameSubsetAccuracy":sum(int(
           (x["probabilities"]["frozen_v1"]>=.5)==bool(x["winnerA"])
       ) for x in chosen)/n if n else None,
    }


def select_rule(valid):
    """Only 2025 H2 labels may select the risk filter. Never use 2026 here."""
    scored=[(rule,score(valid,rule)) for rule in RULES]
    usable=[(r,s) for r,s in scored
       if s["selected"]>=MIN_SELECTED_VALIDATION and
          s["coverage"]>=MIN_VALIDATION_COVERAGE]
    if not usable:
        selected=RULES[0]
        reason="No alternative passed minimum coverage; use fixed baseline only"
    else:
        # Fixed objective: Wilson lower bound, then coverage, then source order.
        selected=max(usable,key=lambda z:(
          z[1]["wilson95Lower"],z[1]["coverage"],-RULES.index(z[0])))[0]
        reason="Best 2025 H2 Wilson lower bound with >=30 selections and >=20% coverage"
    return selected,reason,[{"rule":r["id"],"2025Selection":s} for r,s in scored]


def quarter(date):
    month=int(date[5:7])
    return "Q"+str(1+(month-1)//3)


def diagnostic(rows):
    issues=collections.defaultdict(list)
    all_fights=score(rows,RULES[0])
    for x in rows:
        f=flags(x)
        for key,v in f.items():
            if v:issues[key].append(x)
    out={}
    for k,items in issues.items():
        correct=sum(int(
            (x["probabilities"][BASE_MODEL]>=.5)==bool(x["winnerA"])
        ) for x in items)
        out[k]={"count":len(items),"correct":correct,
                "accuracy":correct/len(items),
                "note":"Overlapping segments, exploratory, not predictive thresholds"}
    failures=[x for x in rows if
              (x["probabilities"][BASE_MODEL]>=.5)!=bool(x["winnerA"])]
    failure_flags=collections.Counter(k for x in failures for k,v in flags(x).items() if v)
    return {"n":len(rows),"fullModelCorrect":len(rows)-len(failures),
        "fullModelAccuracy":1-len(failures)/len(rows) if rows else None,
        "baseline65":all_fights,
        "segments":out,"errorFlagCounts":dict(failure_flags)}


def run(cases):
    if (cases.get("schema")!="JSA_FRONTIER_CASES_V1" or
        cases.get("model")!="nonlinear_ensemble"):
        raise ValueError("Unexpected model case source")
    valid=validate(cases["selection2025"],"2025",want=146)
    hold=validate(cases["development2026"],"2026",want=266)
    if any(x["date"]<"2025-07-01" or x["date"]>="2026-01-01" for x in valid):
        raise ValueError("Validation data includes data outside 2025 H2")
    if any(x["date"]<"2026-01-01" or x["date"]>="2026-11-19" for x in hold):
        raise ValueError("Development includes future or wrong-period fights")
    chosen,reason,val_scores=select_rule(valid)
    whole={r["id"]:score(hold,r) for r in RULES}
    grouped={}
    for q in ("Q1","Q2","Q3","Q4"):
        x=[r for r in hold if quarter(r["date"])==q]
        if not x:raise ValueError("Missing development quarter "+q)
        grouped[q]={"riskAudit":diagnostic(x),
                    "validationSelectedPolicy":score(x,chosen)}
    report={
      "schema":"JSA_FRONTIER_RESILIENCE_V1",
      "baseModel":"2025 H2-selected nonlinear_ensemble",
      "sourceOfTruth":"results/frontier_cases.json from pinned model run",
      "forecastModelChanged":False,
      "policyLockedBefore2026Analysis":False,
      "qualification":"2025-only guard selection, but the underlying 2026 cohort was previously examined in project development",
      "selectedRiskRule":chosen,"selectionReason":reason,
      "validation2025Count":len(valid),"development2026Count":len(hold),
      "selection2025AllCandidates":val_scores,
      "selectedRuleValidation2025":score(valid,chosen),
      "selectedRuleDevelopment2026":score(hold,chosen),
      "riskRulesDevelopment2026_DiagnosticOnly":whole,
      "quarterly2026":grouped,
      "finalStatus":"NO AUTOMATIC POLICY PROMOTION. Prospective independent events are required.",
      "noBettingActions":True,"accuracy99_9Verified":False,"roiVerified":False,
      "disclaimer":"Historical backtest. Risk flags are descriptive and overlap. No independently executable betting prices or prospective accuracy established."
    }
    return report


def main():
    root=Path(__file__).resolve().parents[1]
    source=root/"results/frontier_cases.json"
    report=run(json.loads(source.read_text(encoding="utf-8")))
    output=root/"results/frontier_resilience.json"
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({
      "selectedOn2025":report["selectedRiskRule"]["id"],
      "validation":report["selectedRuleValidation2025"],
      "retrospective2026":report["selectedRuleDevelopment2026"],
      "q4":report["quarterly2026"]["Q4"],
      "noPolicyPromotion":True
    },indent=2,allow_nan=False))


if __name__=="__main__":
    main()
