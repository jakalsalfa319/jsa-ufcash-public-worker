#!/usr/bin/env python3
"""Locked R25k UF1Cash virtual challenge. No real bets, no bookmaker connections."""
from __future__ import annotations
import argparse
import copy
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from scripts.all_in_challenge import cents, zar, plan_round

SCHEMA = "UF1CASH_GOAL_STATUS_V1"
POLICY = "UF1CASH_LOCKED_25K_CHALLENGE_V1"
ACTIVE = ("UFC", "F1", "RUGBY_UNION", "HORSE_RACING", "CRICKET")
TWO_PLACES = Decimal("0.01")


def status(wallet: dict, policy: dict) -> dict:
    if policy.get("schema") != POLICY or policy.get("virtualGoalZAR") != "25000.00":
        raise ValueError("R25k goal must remain locked")
    if policy.get("allInShareOfAvailableBalance") != "1.00":
        raise ValueError("All-in percentage must remain 100%")
    if policy.get("topUpsAllowed") is not False or policy.get("realBettingAllowed") is not False:
        raise ValueError("Only imaginary funds; no top-ups")
    if policy.get("allowedSports") != list(ACTIVE) or policy.get("developmentFocusPercent") != {"UFC":50, "F1":12.5, "RUGBY_UNION":12.5, "HORSE_RACING":12.5, "CRICKET":12.5}:
        raise ValueError("Only the five approved sports are permitted")
    if policy.get("maySuggestChallengeReplacementBeforeGoal") is not False or policy.get("automaticStrategyChangeAtGoal") is not False:
        raise ValueError("No strategy replacement before reaching R25k")
    if policy.get("postGoalChangeRequiresUserApproval") is not True:
        raise ValueError("Strategy changes require approval")
    if wallet.get("schema") != "UF1CASH_VIRTUAL_LEDGER_V2":
        raise ValueError("Wrong active wallet ledger")
    active = wallet["prospectiveWallet"]
    if active.get("balanceAvailableZAR") != wallet.get("currentBalanceZAR"):
        raise ValueError("Available balance and current balance disagree")
    if active.get("topUpsAllowed") is not False or active.get("realFundsZAR") != "0.00":
        raise ValueError("Real funds or top-ups are not allowed")
    if active.get("originIncludesRetrospectiveScenario") is not True:
        raise ValueError("Historical credit must remain explicitly labelled")
    if wallet.get("developmentFocusPercent") != {"UFC":75, "F1":25} or wallet.get("eligibleForwardSports") != list(ACTIVE):
        raise ValueError("Unexpected active-sport focus")
    if any(not str(v).startswith("ON_HOLD") for v in wallet.get("researchBench", {}).values()):
        raise ValueError("Bench sports must remain on hold")
    balance = cents(active["balanceAvailableZAR"])
    pending = cents(active.get("pendingOriginalStakeZAR","0.00"))
    if balance < 0 or pending < 0:
        raise ValueError("Negative virtual balance")
    goal = cents("25000.00")
    reached = balance >= goal
    left = max(0,goal-balance)
    progress = (Decimal(min(balance,goal))*100/Decimal(goal)).quantize(TWO_PLACES,rounding=ROUND_HALF_UP)
    phase = ("GOAL_REACHED_REVIEW_PERMITTED" if reached else
             "NO_AVAILABLE_CASH_RESULTS_PENDING" if balance==0 and pending>0 else
             "BANKRUPT_NO_TOPUPS" if balance==0 else "ACTIVE_UNDER_R25000")
    return {
        "schema":SCHEMA, "challengeId":policy["challengeId"],"currency":"ZAR",
        "originalVirtualCapitalZAR":"2000.00",
        "availableBalanceZAR":zar(balance),"lockedHistoricalPendingStakeZAR":zar(pending),
        "targetBalanceZAR":zar(goal),"toGoZAR":zar(left),"progressPercent":str(progress),
        "goalReached":reached,"challengePhase":phase,
        "nextQualifiedRoundStakeZAR":zar(balance),
        "allInAllocationPercent":100,"uncommittedAfterQualifyingRoundZAR":"0.00",
        "allowedSports":list(ACTIVE),"developmentFocusPercent":{"UFC":50,"F1":12.5,"RUGBY_UNION":12.5,"HORSE_RACING":12.5,"CRICKET":12.5},
        "researchFocusIsNotStakeSplit":True,
        "skipUnqualifiedMarkets":True,"noTopUps":True,
        "strategyReplacementSuggestionAllowed":reached,"strategyChangeRequiresApproval":True,
        "automaticStrategySwitch":False,"realBetsPlaced":0,
        "genuineForwardBetsRecorded":active.get("validPreEventPaperSelections",0),
        "openingWalletIncludesUserAdoptedHistoricalHypotheticalCredit":True,
        "historicReturnsAreNotAuthenticatedPreEventBets":True,
        "disclosure":"All amounts are virtual ZAR. The Qatar balance is retrospectively adopted and does not establish pre-event profitability."
    }


def prepare(wallet: dict, policy: dict, input_data: dict, now=None) -> dict:
    s = status(wallet,policy)
    if cents(s["availableBalanceZAR"]) <= 0:
        raise ValueError("No available virtual bankroll to commit")
    if cents(input_data.get("availableBankrollZAR")) != cents(s["availableBalanceZAR"]):
        raise ValueError("The next round must use the current wallet, not an old or pending balance")
    if Decimal(str(input_data.get("minEstimatedEV","0.03"))) < Decimal(policy["minEstimatedEV"]):
        raise ValueError("Model-estimated EV gate may not be lowered")
    if Decimal(str(input_data.get("maxQuoteAgeMinutes",120))) > Decimal(str(policy["maxQuoteAgeMinutes"])):
        raise ValueError("Quote freshness gate may not be relaxed")
    for item in input_data.get("candidates",[]):
        if item.get("sport") not in ACTIVE:
            raise ValueError("Only UFC, F1, rugby union, horse racing and cricket are permitted")
    receipt=plan_round(copy.deepcopy(input_data),now=now)
    available=cents(s["availableBalanceZAR"])
    if receipt["status"]=="ALL_IN_FROZEN":
        if cents(receipt["deployedZAR"]) != available or receipt["uncommittedZAR"]!="0.00":
            raise ValueError("Every qualified round must stake every available cent")
    elif receipt["status"]=="ABSTAIN_NO_QUALIFIED_MARKET":
        if receipt["deployedZAR"]!="0.00" or cents(receipt["uncommittedZAR"])!=available:
            raise ValueError("Abstaining must preserve the entire balance")
    else:
        raise ValueError("Unrecognized paper round")
    return {"schema":"UF1CASH_GOAL_GATED_ROUND_V1",
            "challengeId":policy["challengeId"],
            "sourceBalanceZAR":s["availableBalanceZAR"],
            "receipt":receipt,"realFundsZAR":"0.00",
            "disclosure":"Prospective research receipt only. URLs and local SHA do not authenticate bookmaker fills."}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("state","prepare"))
    p.add_argument("--wallet",type=Path,required=True)
    p.add_argument("--policy",type=Path,required=True)
    p.add_argument("--input",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    w=json.loads(a.wallet.read_text(encoding="utf-8"))
    pol=json.loads(a.policy.read_text(encoding="utf-8"))
    if a.action=="state":
        result=status(w,pol)
    else:
        if a.input is None:p.error("--input required for prepare")
        result=prepare(w,pol,json.loads(a.input.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False,allow_nan=False)
        f.write("\n")
    print(json.dumps({"virtualOnly":True,"status":result.get("challengePhase",result.get("receipt",{}).get("status")),
        "availableZAR":result.get("availableBalanceZAR",result.get("sourceBalanceZAR"))},indent=2))


if __name__=="__main__":
    main()
