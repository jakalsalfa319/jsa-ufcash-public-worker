#!/usr/bin/env python3
"""Prospective UFC classification evaluator. Standard library only.

CSV columns:
fight_id,fight_utc,feature_asof_utc,prediction_utc,p_a,outcome_a,selected
Optional: decimal_odds_selected,quote_utc,source_name
Times MUST include timezone. p_a = win probability of fighter A.
selected 1 = precommitted prediction; 0 = abstention.
No draw/no-contest/unfinished event may be scored as a win.
"""
import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path


def timestamp(raw):
    value = str(raw or "").strip()
    if not value:
        raise ValueError("Required timestamp missing")
    t = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.utcoffset() is None:
        raise ValueError("Timezone required: " + value)
    return t.astimezone(dt.timezone.utc)


def wilson_lower(wins, total, z=1.959963984540054):
    if total <= 0:
        return None
    phat = wins / total
    denom = 1 + z * z / total
    center = phat + z * z / (2 * total)
    spread = z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total)
    return max(0.0, (center - spread) / denom)


def audit(rows, train_cutoff, min_claim_count=1000):
    """Fail closed on duplicate results, post-event features and quote lookahead."""
    cutoff = timestamp(train_cutoff)
    seen = set()
    parsed = []
    for lineno, row in enumerate(rows, 2):
        fight_id = str(row.get("fight_id", "")).strip()
        if not fight_id or fight_id in seen:
            raise ValueError(f"Line {lineno}: missing or duplicate fight_id")
        seen.add(fight_id)
        fight_at = timestamp(row.get("fight_utc"))
        features_at = timestamp(row.get("feature_asof_utc"))
        predicted_at = timestamp(row.get("prediction_utc"))
        if not (cutoff < fight_at and features_at <= predicted_at < fight_at):
            raise ValueError(f"Line {lineno}: timeline violation")
        p = float(row.get("p_a", "nan"))
        if not (math.isfinite(p) and 0 < p < 1):
            raise ValueError(f"Line {lineno}: invalid probability")
        outcome_raw = str(row.get("outcome_a", "")).strip()
        if outcome_raw not in ("0", "1"):
            raise ValueError(f"Line {lineno}: only completed decisive fights can be scored")
        actual = int(outcome_raw)
        selected_raw = str(row.get("selected", "")).strip()
        if selected_raw not in ("0", "1"):
            raise ValueError(f"Line {lineno}: selected must equal 0 or 1")
        odds_raw = str(row.get("decimal_odds_selected", "") or "").strip()
        quote_raw = str(row.get("quote_utc", "") or "").strip()
        odds = None
        if odds_raw or quote_raw:
            if not odds_raw or not quote_raw:
                raise ValueError(f"Line {lineno}: odds and timestamp must both exist")
            odds = float(odds_raw)
            if not (math.isfinite(odds) and 1.01 <= odds <= 1000):
                raise ValueError(f"Line {lineno}: invalid decimal odds")
            if timestamp(quote_raw) > predicted_at:
                raise ValueError(f"Line {lineno}: quote later than prediction")
        correct = (p >= 0.5) == bool(actual)
        parsed.append((p, actual, selected_raw == "1", correct, odds))
    if not parsed:
        raise ValueError("No completed fight observations supplied")
    chosen = [r for r in parsed if r[2]]
    n = len(chosen)
    wins = sum(int(r[3]) for r in chosen)
    e = 1e-12
    brier = sum((p - y) ** 2 for p, y, *_ in chosen) / n if n else None
    logloss = -sum(y * math.log(max(e, min(1-e, p))) +
                   (1-y) * math.log(max(e, min(1-e, 1-p)))
                   for p, y, *_ in chosen) / n if n else None
    ece = None
    if n:
        bins = [[] for _ in range(10)]
        for p, y, *_ in chosen:
            bins[min(9, int(p * 10))].append((p, y))
        ece = sum((len(b) / n) *
                  abs(sum(p for p, _ in b) / len(b) -
                      sum(y for _, y in b) / len(b))
                  for b in bins if b)
    illustrative_roi = None
    if n and all(r[4] is not None for r in chosen):
        illustrative_roi = sum((r[4] - 1) if r[3] else -1 for r in chosen) / n
    lower = wilson_lower(wins, n)
    technical_gate = bool(n >= min_claim_count and lower is not None and lower >= 0.999)
    return {
        "completed_fights": len(parsed), "selected_predictions": n,
        "abstained": len(parsed) - n, "coverage": n / len(parsed),
        "correct": wins, "selected_accuracy": wins / n if n else None,
        "wilson_95_lower": lower, "brier_selected": brier,
        "log_loss_selected": logloss, "ece_10_bins_selected": ece,
        "illustrative_roi_unverified_odds": illustrative_roi,
        "reference_odds_are_not_verified_executable": True,
        "technical_99_9_gate_met": technical_gate,
        "verified_99_9_claim": False,
        "disclaimer": "Statistical gates cannot establish independent lockbox integrity, correct training history, profitable betting or executable odds. External evaluation is required."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions_csv", type=Path)
    parser.add_argument("--train-cutoff-utc", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with args.predictions_csv.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    result = audit(rows, args.train_cutoff_utc)
    payload = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
