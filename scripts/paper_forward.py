#!/usr/bin/env python3
"""J$A UFCash forward-only, no-money paper decision journal.

The frozen snapshot is a point-in-time research receipt, not an authenticated
bookmaker ticket. Manual/public quotes are NEVER represented as executable.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlparse

INPUT_SCHEMA = "JSA_UFCASH_FORWARD_INPUT_V1"
SNAPSHOT_SCHEMA = "JSA_UFCASH_FORWARD_SNAPSHOT_V1"
SETTLEMENT_SCHEMA = "JSA_UFCASH_FORWARD_RECONCILIATION_V1"
STATUSES = {"COMPLETED", "PENDING", "DRAW", "NO_CONTEST", "CANCELLED", "POSTPONED", "REPLACED", "DISPUTED"}
OFFICIAL_HOSTS = {"ufcstats.com", "www.ufcstats.com", "ufc.com", "www.ufc.com", "us.ufcespanol.com", "ufcespanol.com"}


def utc(value: str) -> dt.datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("UTC ISO timestamp required")
    try:
        val = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid timestamp") from exc
    if val.tzinfo is None or val.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required")
    return val.astimezone(dt.timezone.utc)


def iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def hash_payload(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                                     allow_nan=False).encode("utf-8")).hexdigest()


def valid_url(value: str, official: bool = False) -> bool:
    try:
        parsed = urlparse(value)
    except (ValueError, TypeError):
        return False
    return (parsed.scheme == "https" and bool(parsed.hostname) and bool(parsed.path)
            and not (parsed.username or parsed.password)
            and (not official or parsed.hostname in OFFICIAL_HOSTS))


def price(american: int) -> float:
    if type(american) is not int or -100 < american < 100:
        raise ValueError("American odds must be integer <=-100 or >=100")
    return 1 + american / 100 if american > 0 else 1 + 100 / -american


def prob(value) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value < 1:
        raise ValueError("Probability must be strictly between 0 and 1")
    return float(value)


def pair_key(red: str, blue: str) -> str:
    if not isinstance(red, str) or not isinstance(blue, str):
        raise ValueError("Fighter names required")
    red, blue = red.strip(), blue.strip()
    if not red or not blue or red.casefold() == blue.casefold():
        raise ValueError("Invalid fighter pair")
    return "|".join(sorted([red.casefold(), blue.casefold()]))


def freeze(data: dict, now: dt.datetime | None = None) -> dict:
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    if data.get("schema") != INPUT_SCHEMA:
        raise ValueError("Unknown forward paper input schema")
    event_start = utc(data["eventStartUTC"])
    if not now < event_start:
        raise ValueError("No retrospective paper tickets: event has started")
    captured = utc(data["predictionsCapturedAtUTC"])
    if captured > now or captured >= event_start:
        raise ValueError("Model predictions were not captured before the event")
    if not valid_url(data.get("predictionSourceUrl")):
        raise ValueError("Model prediction source URL required")
    source_hash = data.get("predictionSourceSha256")
    if not isinstance(source_hash, str) or len(source_hash) != 64 or any(x not in "0123456789abcdef" for x in source_hash):
        raise ValueError("Immutable model input source SHA-256 required")
    event_id = data.get("eventId")
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("Event ID required")

    pol = data.get("policy", {})
    bankroll = pol.get("demoBankroll", 1000)
    frac = pol.get("stakeFraction", 0.01)
    cap = pol.get("maxTotalExposureFraction", 0.05)
    threshold = pol.get("minExpectedRoi", 0.03)
    age = pol.get("maxQuoteAgeMinutes", 120)
    if any(type(v) not in (float, int) or not math.isfinite(v) for v in (bankroll, frac, cap, threshold, age)):
        raise ValueError("Invalid money/threshold policy values")
    if not (bankroll > 0 and 0 < frac <= 0.01 and frac <= cap <= 0.05 and 0 <= threshold <= 1 and 0 < age <= 1440):
        raise ValueError("Unsafe paper staking/age policy")
    max_risk = round(bankroll * cap, 2)
    stake = round(bankroll * frac, 2)
    if stake <= 0:
        raise ValueError("Demo stake rounds to zero")

    fights = data.get("fights", [])
    if not isinstance(fights, list) or not fights:
        raise ValueError("At least one fight is needed")
    seen, rows, candidates = set(), [], []
    for i, f in enumerate(fights):
        key = pair_key(f.get("red"), f.get("blue"))
        if key in seen:
            raise ValueError("Duplicate fighter matchup")
        seen.add(key)
        row = {"red": f["red"], "blue": f["blue"], "boutId": key, "status": "NO_PAPER_ORDER",
               "reason": None, "modelPRed": None, "quote": None, "candidate": None}
        p = f.get("modelPRed")
        if p is None:
            row["reason"] = "MISSING_MODEL_PROBABILITY"
            rows.append(row)
            continue
        p = prob(p)
        row["modelPRed"] = p
        quote = f.get("quote")
        if quote is None:
            row["reason"] = "MISSING_PRICE_SNAPSHOT"
            rows.append(row)
            continue
        qtime = utc(quote["capturedAtUTC"])
        if not captured <= qtime <= now:
            raise ValueError("Quote was not chronologically captured after model forecast and before freeze")
        if qtime >= event_start:
            raise ValueError("Quote captured after the event started")
        if (now - qtime).total_seconds() > age * 60:
            row["reason"] = "STALE_QUOTE"
            rows.append(row)
            continue
        if not valid_url(quote.get("sourceUrl")) or not quote.get("sourceName"):
            row["reason"] = "UNATTRIBUTED_QUOTE"
            rows.append(row)
            continue
        red_decimal, blue_decimal = price(quote["redAmerican"]), price(quote["blueAmerican"])
        row["quote"] = {"capturedAtUTC": iso(qtime), "sourceName": quote["sourceName"],
                        "sourceUrl": quote["sourceUrl"], "redAmerican": quote["redAmerican"],
                        "blueAmerican": quote["blueAmerican"], "verifiedExecutable": False,
                        "type": "MANUAL_PUBLIC_REFERENCE_NOT_EXECUTABLE"}
        best = max([(p * red_decimal - 1, f["red"], red_decimal, p),
                    ((1 - p) * blue_decimal - 1, f["blue"], blue_decimal, 1 - p)], key=lambda x: x[0])
        expected, side, odds, sidep = best
        row["candidate"] = {"selection": side, "decimalOdds": round(odds, 8),
                            "selectionProbability": sidep, "expectedRoiAssumingModelCalibrated": round(expected, 8)}
        if expected < threshold:
            row["reason"] = "BELOW_PRELOCKED_EV_THRESHOLD"
        else:
            candidates.append((expected, i))
        rows.append(row)

    exposure, count = 0.0, 0
    for _, i in sorted(candidates, key=lambda x: (-x[0], x[1])):
        r = rows[i]
        if round(exposure + stake, 2) > max_risk:
            r["reason"] = "TOTAL_EXPOSURE_CAP"
            continue
        r["status"] = "PAPER_DECISION_RECORDED"
        r["reason"] = "NO_EXECUTABLE_ODDS_PROOF"
        r["mockStake"] = stake
        exposure = round(exposure + stake, 2)
        count += 1

    raw = {"schema": SNAPSHOT_SCHEMA, "eventId": event_id, "eventStartUTC": iso(event_start),
           "frozenAtUTC": iso(now), "predictionsCapturedAtUTC": iso(captured),
           "predictionSourceUrl": data["predictionSourceUrl"], "predictionSourceSha256": source_hash,
           "modelId": data.get("modelId", "unknown"),
           "policy": {"demoBankroll": bankroll, "stakeFraction": frac, "maxTotalExposureFraction": cap,
                      "maxQuoteAgeMinutes": age, "minExpectedRoi": threshold},
           "fights": rows, "paperDecisionCount": count, "demoExposure": exposure,
           "fundsUsed": 0, "realBetsPlaced": 0, "autoBettingEnabled": False,
           "verifiedExecutableOdds": False, "validatedPaperRoi": None,
           "warning": "Public reference/manual quote; model EV is not a verified betting edge. Snapshot SHA alone does not authenticate source time."}
    raw["snapshotSha256"] = hash_payload(raw)
    return raw


def settle(snapshot: dict, results: dict, now: dt.datetime | None = None) -> dict:
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    original = {k: v for k, v in snapshot.items() if k != "snapshotSha256"}
    if snapshot.get("schema") != SNAPSHOT_SCHEMA or hash_payload(original) != snapshot.get("snapshotSha256"):
        raise ValueError("Snapshot corrupted or modified; frozen model/order audit failed")
    if snapshot["fundsUsed"] != 0 or snapshot["realBetsPlaced"] != 0:
        raise ValueError("Unexpected live transactions")
    if not now >= utc(snapshot["eventStartUTC"]):
        raise ValueError("Cannot settle a future event")
    if results.get("eventId") != snapshot["eventId"]:
        raise ValueError("Event identity mismatch")
    by_key = {r["boutId"]: r for r in snapshot["fights"]}
    input_rows = results.get("outcomes", [])
    if not isinstance(input_rows, list):
        raise ValueError("Outcomes must be a list")
    observed = {}
    for r in input_rows:
        key = pair_key(r.get("red"), r.get("blue"))
        if key not in by_key or key in observed:
            raise ValueError("Duplicate/unrecognized results fighter pair")
        status = r.get("status")
        if status not in STATUSES:
            raise ValueError("Invalid result status")
        winner = r.get("winner")
        if status == "COMPLETED":
            if winner not in (by_key[key]["red"], by_key[key]["blue"]):
                raise ValueError("Completed bout needs original fighter winner")
            if not valid_url(r.get("sourceUrl"), official=True):
                raise ValueError("Official result source URL required")
            checked = utc(r["observedAtUTC"])
            if checked < utc(snapshot["eventStartUTC"]) or checked > now:
                raise ValueError("Outcome evidence timestamp impossible")
        else:
            if winner:
                raise ValueError("Non-completed bout cannot record winner")
            if status not in ("PENDING", "DISPUTED") and not valid_url(r.get("sourceUrl"), official=True):
                raise ValueError("Official status source URL required")
        observed[key] = r

    records, accuracy, probs, pnl, peak, bankroll, completed_decisions = [], [], [], 0.0, 0.0, 0.0, 0
    for original_row in snapshot["fights"]:
        key = original_row["boutId"]
        r = observed.get(key, {"status": "PENDING"})
        win = r.get("winner") if r["status"] == "COMPLETED" else None
        correct = None
        if win is not None and original_row["modelPRed"] is not None:
            p = original_row["modelPRed"]
            outcome_red = int(win == original_row["red"])
            accuracy.append(int((p >= .5) == bool(outcome_red)))
            probs.append((p, outcome_red))
            correct = bool(accuracy[-1])
        paper_net = None
        if win is not None and original_row["status"] == "PAPER_DECISION_RECORDED":
            bet = original_row["candidate"]
            stake = original_row["mockStake"]
            paper_net = round((stake * (bet["decimalOdds"] - 1)) if bet["selection"] == win else -stake, 2)
            pnl = round(pnl + paper_net, 2)
            peak = max(peak, pnl)
            completed_decisions += 1
        records.append({"red": original_row["red"], "blue": original_row["blue"], "status": r["status"],
                        "claimedWinner": win, "modelPickCorrectAgainstClaimedResult": correct,
                        "decision": original_row["status"], "scenarioNet": paper_net,
                        "resultSourceUrl": r.get("sourceUrl"), "resultContentIndependentlyVerified": False})
    brier = sum((p-y)**2 for p, y in probs) / len(probs) if probs else None
    final = {"schema": SETTLEMENT_SCHEMA, "eventId": snapshot["eventId"],
             "reconciledAtUTC": iso(now), "originalSnapshotSha256": snapshot["snapshotSha256"],
             "totalFights": len(records), "reportedDecisiveModelFights": len(accuracy),
             "modelWinnerAccuracyAgainstClaimedResults": sum(accuracy)/len(accuracy) if accuracy else None,
             "brierAgainstClaimedResults": brier,
             "completedPaperDecisionsAgainstClaimedResults": completed_decisions,
             "scenarioNetAgainstClaimedResults": pnl,
             "scenarioROIOnCompletedStake": (pnl / (completed_decisions * round(snapshot["policy"]["demoBankroll"] * snapshot["policy"]["stakeFraction"], 2)) if completed_decisions else None),
             "verifiedPaperRoi": None, "realFundsUsed": 0, "realBetsPlaced": 0,
             "sourceContentsIndependentlyAudited": False, "status": "CLAIMED_RESULTS_NOT_INDEPENDENTLY_AUDITED",
             "bouts": records,
             "warning": "Result URLs and manual quotes alone are not independently verified evidence; this is scenario accounting only."}
    final["reconciliationSha256"] = hash_payload(final)
    return final


def write_new(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as out:  # never overwrite a journal
        json.dump(value, out, indent=2, ensure_ascii=False, allow_nan=False)
        out.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    a = commands.add_parser("freeze", help="Freeze input before event; source data must really be pre-event")
    a.add_argument("--input", required=True, type=Path)
    a.add_argument("--output", required=True, type=Path)
    a = commands.add_parser("reconcile", help="Score externally asserted results without promoting to verified")
    a.add_argument("--snapshot", required=True, type=Path)
    a.add_argument("--outcomes", required=True, type=Path)
    a.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "freeze":
        record = freeze(json.loads(args.input.read_text(encoding="utf-8")))
    else:
        record = settle(json.loads(args.snapshot.read_text(encoding="utf-8")),
                        json.loads(args.outcomes.read_text(encoding="utf-8")))
    write_new(args.output, record)
    print(json.dumps({k: record.get(k) for k in ("schema", "eventId", "snapshotSha256", "paperDecisionCount",
                                                       "status", "realBetsPlaced") if k in record}, indent=2))


if __name__ == "__main__":
    main()