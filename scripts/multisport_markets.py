#!/usr/bin/env python3
"""Turn fully attributed rugby 1X2 / horse WIN probability boards into R0 paper candidates.

This module is a validation and market-selection adapter, NOT a trained
predictive model or an odds collector. Accepts no incomplete or scratched race.
Synthetic test values do not qualify as historic/prospective betting evidence.
"""
from __future__ import annotations
from decimal import Decimal
from scripts.all_in_challenge import d, quoted_decimal, timestamp, url_good

RUGBY_SCHEMA = "UFCASH_RUGBY_UNION_1X2_BOARD_V1"
HORSE_SCHEMA = "UFCASH_HORSE_FIXED_WIN_BOARD_V1"
CRICKET_SCHEMA = "UF1CASH_CRICKET_T20_MATCH_WINNER_BOARD_V1"


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " missing")
    return value.strip()


def _probabilities(items):
    probs = [d(x) for x in items]
    if any(not 0 < p < 1 for p in probs):
        raise ValueError("Each probability must be strictly between zero and one")
    if abs(sum(probs) - Decimal("1")) > Decimal("0.000001"):
        raise ValueError("Complete market probabilities must sum to one")
    return probs


def _quote(board):
    q = board.get("quote")
    if not isinstance(q, dict):
        raise ValueError("Missing source-attributed quote")
    stamp = timestamp(q.get("capturedAtUTC"))
    name = _text(q.get("sourceName"), "Quote provider")
    if not url_good(q.get("sourceUrl")):
        raise ValueError("Missing legitimate HTTPS price source")
    if q.get("priceKind") != "FIXED_DECIMAL":
        raise ValueError("Tote dividends and indicative forecast prices are not fixed-odds quotes")
    return q, stamp, name


def _eligible_board(board, schema, expected_market):
    if board.get("schema") != schema:
        raise ValueError("Incorrect market schema")
    if board.get("market") != expected_market:
        raise ValueError("Wrong market settlement definition")
    eid = _text(board.get("eventId"), "Event id")
    start = timestamp(board.get("eventStartsUTC"))
    q, captured, source = _quote(board)
    if captured >= start:
        raise ValueError("Price captured at or after event start")
    return eid, start, q, source


def _select(event_id, start, board, source, sides, sport, market):
    # Each side includes key, selection name, valid probability and decimal quote.
    rows = []
    for key, name, probability, quote in sides:
        decimal_price = quoted_decimal({"decimalOdds": quote})
        ev = probability * decimal_price - 1
        rows.append((ev, key, name, probability, decimal_price))
    # Deterministic label tie-break; never multiple sides of one event.
    ev, key, name, probability, price = sorted(rows, key=lambda x: (-x[0], x[1]))[0]
    return {
        "eventId": event_id, "sport": sport, "market": market,
        "selection": name, "eventStartsUTC": board["eventStartsUTC"],
        "modelPSelection": str(probability),
        "quote": {"decimalOdds": str(price), "capturedAtUTC": board["quote"]["capturedAtUTC"],
                  "sourceUrl": board["quote"]["sourceUrl"], "sourceName": source},
        "weight": 1,
        "sourceBoardSchema": board["schema"],
        "modelEstimatedEV": str(ev),
    }


def rugby_union_candidate(board):
    """Regulation 80 minutes ONLY, 3-way home/draw/away, excludes extra time."""
    eid, start, q, source = _eligible_board(board, RUGBY_SCHEMA, "REGULATION_80_MIN_1X2")
    if board.get("fixtureStatus") != "CONFIRMED_PREMATCH":
        raise ValueError("Rugby fixture not confirmed pre-match")
    home = _text(board.get("homeTeam"), "Home team")
    away = _text(board.get("awayTeam"), "Away team")
    if home.casefold() == away.casefold():
        raise ValueError("Home/away identities are equal")
    probabilities = board.get("modelProbabilities")
    prices = q.get("pricesDecimal")
    keys = ("home", "draw", "away")
    if not isinstance(probabilities, dict) or set(probabilities) != set(keys):
        raise ValueError("Require home, draw, away probabilities")
    if not isinstance(prices, dict) or set(prices) != set(keys):
        raise ValueError("Require complete 1X2 fixed odds")
    probs = _probabilities([probabilities[k] for k in keys])
    sides = [("home", home, probs[0], prices["home"]),
             ("draw", "DRAW", probs[1], prices["draw"]),
             ("away", away, probs[2], prices["away"])]
    return _select(eid, start, board, source, sides, "RUGBY_UNION", "REGULATION_80_MIN_1X2")


def horse_win_candidate(board):
    """Only a full, current field of declared runners with fixed WIN odds.

    Scratchings require refreshing/recalculating the full model and market.
    Dead heats and rule-4 / price deductions require separate settlement.
    """
    eid, start, q, source = _eligible_board(board, HORSE_SCHEMA, "FIXED_WIN")
    if board.get("raceStatus") != "CONFIRMED_DECLARATIONS":
        raise ValueError("Race not confirmed / declarations not current")
    _text(board.get("course"), "Racecourse")
    runners = board.get("runners")
    if not isinstance(runners, list) or not 2 <= len(runners) <= 40:
        raise ValueError("Require complete 2-40 runner field")
    names, ids = set(), set()
    for runner in runners:
        if not isinstance(runner, dict):
            raise ValueError("Invalid runner")
        name = _text(runner.get("horseName"), "Horse name")
        ident = _text(runner.get("runnerId"), "Runner id")
        if name.casefold() in names or ident in ids:
            raise ValueError("Duplicate runner")
        names.add(name.casefold()); ids.add(ident)
        if runner.get("status") != "DECLARED":
            raise ValueError("Scratched/withdrawn runner: freeze entire race until repriced")
    probs = _probabilities([r.get("modelWinProbability") for r in runners])
    prices = q.get("pricesDecimalByRunnerId")
    if not isinstance(prices, dict) or set(prices) != ids:
        raise ValueError("Every declared runner needs a genuine fixed WIN quote")
    sides = [(r["runnerId"], r["horseName"], p, prices[r["runnerId"]]) for r,p in zip(runners,probs)]
    return _select(eid, start, board, source, sides, "HORSE_RACING", "FIXED_WIN")




def cricket_t20_candidate(board):
    """Two-team prematch T20/T20I winner market INCLUDING any Super Over.

    Void, DLS, tie and abandonment settlement depend on bookmaker rules.
    Returns one candidate; does not generate a model or odds.
    """
    eid, start, q, source = _eligible_board(
        board, CRICKET_SCHEMA, "T20_MATCH_WINNER_INCLUDING_SUPER_OVER")
    if board.get("matchStatus") != "CONFIRMED_PREMATCH":
        raise ValueError("Cricket match not confirmed pre-match")
    if board.get("matchFormat") not in ("T20", "T20I"):
        raise ValueError("Only T20 and T20I are supported")
    team_a = _text(board.get("teamA"), "Team A")
    team_b = _text(board.get("teamB"), "Team B")
    if team_a.casefold() == team_b.casefold():
        raise ValueError("Duplicate cricket team")
    probs = board.get("modelProbabilities")
    prices = q.get("pricesDecimal")
    keys = ("team_a", "team_b")
    if not isinstance(probs, dict) or set(probs) != set(keys):
        raise ValueError("Both teams require model probabilities")
    if not isinstance(prices, dict) or set(prices) != set(keys):
        raise ValueError("Both teams require fixed win odds")
    values = _probabilities([probs[k] for k in keys])
    sides = [("team_a", team_a, values[0], prices["team_a"]),
             ("team_b", team_b, values[1], prices["team_b"])]
    return _select(eid, start, board, source, sides, "CRICKET",
                   "T20_MATCH_WINNER_INCLUDING_SUPER_OVER")

def market_candidate(board):
    if board.get("schema") == RUGBY_SCHEMA:
        return rugby_union_candidate(board)
    if board.get("schema") == HORSE_SCHEMA:
        return horse_win_candidate(board)
    if board.get("schema") == CRICKET_SCHEMA:
        return cricket_t20_candidate(board)
    raise ValueError("Unsupported or unknown market; do not infer outcomes")
