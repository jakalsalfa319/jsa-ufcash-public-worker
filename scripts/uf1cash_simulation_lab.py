#!/usr/bin/env python3
"""Synthetic Monte Carlo stress tests for the UF1Cash R25k all-in challenge.

This is NOT predictive inference, live odds, real gambling, or a genuine bet.
Uses explicit joint outcome scenarios to avoid silently treating correlated
tickets (including different markets on the same event) as independent.
"""
from __future__ import annotations
import argparse
from decimal import Decimal,ROUND_HALF_UP
import json
from pathlib import Path
import random
from scripts.all_in_challenge import cents,zar,d,weights_split
from scripts.uf1cash_challenge import status as current_status

SCHEMA="UF1CASH_SYNTHETIC_ALLIN_STRESS_INPUT_V1"
REPORT="UF1CASH_SYNTHETIC_ALLIN_STRESS_REPORT_V1"
MAX_TRIALS=100000
MAX_ROUNDS=30
MAX_TICKETS=30
CENT=Decimal("1")

def _validate(spec,wallet,policy):
    current=current_status(wallet,policy)
    if not isinstance(spec,dict) or spec.get("schema")!=SCHEMA:
        raise ValueError("Unknown synthetic simulation schema")
    if spec.get("mode")!="SYNTHETIC_ONLY":
        raise ValueError("Cannot treat model forecasts or actual odds as synthetic simulations")
    if cents(spec.get("startingBalanceZAR"))!=cents(current["availableBalanceZAR"]):
        raise ValueError("Synthetic starting amount must match the current virtual wallet")
    if cents(spec.get("targetBalanceZAR"))!=cents(current["targetBalanceZAR"]):
        raise ValueError("Do not change the locked R25k milestone")
    trials=spec.get("trialCount")
    seed=spec.get("seed")
    if type(trials) is not int or not 1<=trials<=MAX_TRIALS:
        raise ValueError("Invalid simulation trial count")
    if type(seed) is not int or not 0<=seed<=4294967295:
        raise ValueError("Deterministic integer random seed required")
    rounds=spec.get("rounds")
    if not isinstance(rounds,list) or not 1<=len(rounds)<=MAX_ROUNDS:
        raise ValueError("1 to 30 synthetic rounds required")
    seen_rounds=set()
    prepared=[]
    for round_ in rounds:
        if not isinstance(round_,dict):
            raise ValueError("Malformed synthetic round")
        ident=round_.get("roundId")
        if not isinstance(ident,str) or not ident.strip() or ident in seen_rounds:
            raise ValueError("Missing or duplicate round ID")
        seen_rounds.add(ident)
        tickets=round_.get("tickets")
        if not isinstance(tickets,list) or not 1<=len(tickets)<=MAX_TICKETS:
            raise ValueError("Missing round tickets")
        ids=[];weights=[]
        for t in tickets:
            if not isinstance(t,dict):raise ValueError("Malformed synthetic ticket")
            name=t.get("ticketId")
            if not isinstance(name,str) or not name or name in ids:
                raise ValueError("Duplicate or missing ticket ID")
            ids.append(name)
            sport=t.get("sport")
            if sport not in current["allowedSports"]:
                raise ValueError("Unapproved sport in simulation")
            weight=d(t.get("weight"))
            if not Decimal("0")<weight<=Decimal("1000000000"):
                raise ValueError("Invalid ticket weight")
            weights.append(weight)
        outcomes=round_.get("jointScenarios")
        if not isinstance(outcomes,list) or not 1<=len(outcomes)<=256:
            raise ValueError("Joint outcome table required; never infer independence")
        probability=Decimal("0");scenarios=[];seen_scenarios=set()
        for outcome in outcomes:
            if not isinstance(outcome,dict):raise ValueError("Malformed outcome")
            label=outcome.get("label")
            if not isinstance(label,str) or not label or label in seen_scenarios:
                raise ValueError("Joint scenario label duplicated or empty")
            seen_scenarios.add(label)
            p=d(outcome.get("probability"))
            if not Decimal("0")<p<=Decimal("1"):
                raise ValueError("Joint scenario probability outside (0,1]")
            pay=outcome.get("grossPayoutMultipliers")
            if not isinstance(pay,dict) or set(pay)!=set(ids):
                raise ValueError("Scenario must describe payout for every ticket exactly once")
            multipliers=[]
            for key in ids:
                multiplier=d(pay[key])
                if not Decimal("0")<=multiplier<=Decimal("1000"):
                    raise ValueError("Unusable gross payout multiplier")
                multipliers.append(multiplier)
            probability+=p
            scenarios.append({"label":label,"probability":p,"multipliers":multipliers})
        if probability!=Decimal("1"):
            raise ValueError("Joint probabilities must sum exactly to one")
        prepared.append({"roundId":ident,"ticketIds":ids,"weights":weights,"scenarios":scenarios})
    return current,prepared

def _percent(count,total):
    return str((Decimal(count)*100/Decimal(total)).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))

def _quantile(sorted_values,fraction):
    ix=int((len(sorted_values)-1)*fraction)
    return zar(sorted_values[ix])

def run(spec,wallet,policy):
    current,rounds=_validate(spec,wallet,policy)
    starting=cents(current["availableBalanceZAR"])
    goal=cents(current["targetBalanceZAR"])
    trials=spec["trialCount"]
    rng=random.Random(spec["seed"])
    end_balances=[]
    finished_at_target=ruin=unfinished=0
    rounds_played=[]
    max_drawdowns=[]
    choices={r["roundId"]:{s["label"]:0 for s in r["scenarios"]} for r in rounds}
    for _ in range(trials):
        balance=starting;peak=balance;max_dd=Decimal("0");used=0
        if balance>=goal:
            finished_at_target+=1
        else:
            for round_ in rounds:
                if balance<=0 or balance>=goal:break
                stakes=weights_split(balance,round_["weights"])
                if sum(stakes)!=balance or min(stakes)<1:
                    raise ValueError("Every synthetic round must allocate every available cent")
                draw=rng.random()
                cumulative=0.0
                picked=round_["scenarios"][-1]
                for scenario in round_["scenarios"]:
                    cumulative+=float(scenario["probability"])
                    if draw<cumulative:
                        picked=scenario
                        break
                choices[round_["roundId"]][picked["label"]]+=1
                balance=sum(int((Decimal(stake)*multiple).quantize(CENT,rounding=ROUND_HALF_UP))
                            for stake,multiple in zip(stakes,picked["multipliers"]))
                used+=1
                peak=max(peak,balance)
                max_dd=max(max_dd,Decimal(peak-balance)/Decimal(peak))
            if balance>=goal:finished_at_target+=1
            elif balance==0:ruin+=1
            else:unfinished+=1
        end_balances.append(balance)
        rounds_played.append(used)
        max_drawdowns.append(max_dd)
    ordered=sorted(end_balances)
    avg=(Decimal(sum(end_balances))/Decimal(trials)).quantize(CENT,rounding=ROUND_HALF_UP)
    mean_dd=(sum(max_drawdowns,Decimal("0"))/Decimal(trials)*100).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
    return {
        "schema":REPORT,"mode":"SYNTHETIC_ONLY","challengeId":policy["challengeId"],
        "createdFrom":"SOURCE_CONTROLLED_HYPOTHETICAL_SCENARIOS",
        "trialCount":trials,"seed":spec["seed"],"plannedRounds":len(rounds),
        "originalAvailableVirtualZAR":zar(starting),
        "disputedHistoricalStakeExcludedZAR":current["lockedHistoricalPendingStakeZAR"],
        "virtualGoalZAR":zar(goal),"allInSharePerQualifyingSyntheticRound":1,
        "reachedGoalCount":finished_at_target,"ruinCount":ruin,
        "survivingBelowGoalCount":unfinished,
        "reachedGoalPercent":_percent(finished_at_target,trials),
        "ruinPercent":_percent(ruin,trials),
        "belowGoalStillAlivePercent":_percent(unfinished,trials),
        "averageFinalVirtualZAR":zar(int(avg)),
        "medianFinalVirtualZAR":_quantile(ordered,0.5),
        "p05FinalVirtualZAR":_quantile(ordered,0.05),
        "p95FinalVirtualZAR":_quantile(ordered,0.95),
        "averageRoundsPlayed":str((Decimal(sum(rounds_played))/Decimal(trials)).quantize(Decimal("0.01"))),
        "averageMaxDrawdownPercent":str(mean_dd),
        "observedSyntheticScenarioCounts":choices,
        "noTopups":True,"noRealBets":True,"noActualForwardVirtualTicketsCreated":True,
        "noAuthoritativeWalletMutation":True,
        "actualProfitEstablished":False,
        "assumptions":["Joint outcome probabilities within each round are user-authored synthetic guesses",
                       "Different rounds are sampled independently, conditional on reaching them",
                       "Gross payout multipliers include stake returns and are synthetic",
                       "A virtual wallet at zero ends without replenishment",
                       "Reaching R25k stops this simulation at the user's approval gate"],
        "note":"These Monte Carlo frequencies are conditional on imaginary probabilities and payouts. They are NOT predictions of actual winning chances."
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--wallet",type=Path,required=True)
    p.add_argument("--policy",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    read=lambda f:json.loads(f.read_text(encoding="utf-8"))
    result=run(read(a.input),read(a.wallet),read(a.policy))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as dest:
        json.dump(result,dest,indent=2,ensure_ascii=False,allow_nan=False)
        dest.write("\n")
    print(json.dumps({"synthetic":True,"goalRatePercent":result["reachedGoalPercent"],
                      "ruinRatePercent":result["ruinPercent"],"realBets":0}))

if __name__=="__main__":
    main()
