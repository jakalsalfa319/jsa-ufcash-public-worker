# UF1Cash Simulation and Forecast Skill Laboratory
**Created 22 November 2026 | Research-only virtual sports forecasting**

## Why simulations matter

Betting outcome accuracy, probability accuracy and virtual profitability are different. A retrospective profit is not a valid forward test. The current R3,071.74 working virtual balance includes a deliberately user-adopted historical scenario rather than verified pre-event tickets, while the original disputed R500 stake remains locked. A predictive advantage has not been shown.

## Added features

1. `scripts/uf1cash_simulation_lab.py` runs deterministic, seeded, *synthetic* Monte Carlo paths with a full joint scenario probability table for EACH proposed round. Every round stakes 100% of whichever virtual balance remains, to the cent; reaching R25,000 or R0 stops the trial. It reports bankruptcy fraction, target attainment, closing balance quantiles, and simulated drawdown. It never credits or modifies the official wallet.
2. `scripts/uf1cash_forecast_skill.py` audits user-supplied pre-event binary forecasts with a chronological integrity gate and source URLs. It reports mean **Brier score**, **log loss**, expected calibration error (ECE), reliability-bin summaries and matched baseline performance. Only definite reviewed outcomes may enter its metrics; disputes remain excluded. Code does not independently authenticate URLs and does not create bets.
3. `public/uf1cash-simulations.html` is a standalone interactive **20,000-path synthetic single-ticket simulator**, linked from the UF1Cash website. Sliders control hypothetical win probability, gross decimal payout and maximum rounds. The more advanced Python simulator supports correlated tickets in a basket.
4. CI regression tests cover ruin, refunds, correlated scenarios, no future information in forecast scoring, full available-balance commitment, the R25,000 milestone and no real-money execution. Daily observations write a **synthetic artifact** but do not change published balances.

## The fundamental evaluation method

Use a frozen, event-time-stamped forecast snapshot *before* the event. Confirm the event identity and market semantics. Acquire results after the event. Group training and test by event and chronology; never use future injuries, winners, odds changes, feature normalization, model selection or results when generating an earlier forecast. Report the time split and compare against **simple baselines**, including a baseline generated from source-observed market probabilities when legal, available and matched.

Measure:
- **Log loss and Brier score**: proper scoring rules, smaller is better; evaluate calibration and sharpness.
- **Calibration charts**: model probabilities vs actual outcome frequencies, with event counts.
- **Expected value**: model probability × source-attributed gross decimal price − 1, but treat uncertain model probabilities and unavailable real quotes honestly.
- **Market baseline**: de-vig (remove the bookmaker margin) only for complete, same-market pre-event price boards, not partial/tote/after-the-fact odds.
- **Uncertainty**: confidence intervals over event-grouped, chronological samples; avoid claiming an advantage from a tiny sample.
- **Live forward tests**: actual pre-event receipts committed before kickoff. The synthetic Monte Carlo results are a *stress test*, not proof of a profitable forecast.

Scientific references: https://scikit-learn.org/stable/modules/calibration.html and https://pmc.ncbi.nlm.nih.gov/articles/PMC13661197/ .

## Five sports: modelling roadmap

- **UFC, 50% of research**: preserve fitted Frontier checkpoint; improve fighter ID matching, pre-fight feature timelines, short-notice cancellations, layoff/injury and weight-class change handling; validate chronological UFC events and calibration independently.
- **F1, 12.5%**: race finish-position distributions and DNF/caution probabilities, qualifying/grid, track conditions and mechanical reliability. Jolpica is a calendar/source reference; check its CC BY-NC-SA terms before commercial use.
- **Rugby union, 12.5%**: Bayesian or Elo team ratings, confirmed line-ups, home advantage, expected points/scoring distributions and *draw probability* for 80-minute 1X2 markets.
- **Horse racing, 12.5%**: complete field-strength model, scratchings, weights, going, distance, draw, pace, jockey/trainer; rank-dependent joint outcomes for fixed WIN/PLACE and exotics. Tote/dividends, dead heats and Rule 4 require dedicated settlement.
- **Cricket, 12.5%**: start with Cricsheet historical T20 ball-by-ball data, team ratings, venue and innings simulation, then toss effects, DLS/abandonments and Super Over semantics. Cricsheet's ODC-BY data attribution must be preserved.

The first goal is **reproducible, source-audited forecasts that beat simple baselines**, not more daily predictions for their own sake.

## Run from the repository root

Simulation:
```bash
python -m scripts.uf1cash_simulation_lab --input research/uf1cash-synthetic-risk-scenarios-v1.json --wallet public/uf1cash-status.json --policy records/uf1cash/challenge-policy-v3.json --output /tmp/uf1cash-synthetic-lab.json
```

Forecast skill audit (once genuine reviewed records are available):
```bash
python -m scripts.uf1cash_forecast_skill --input /path/to/confirmed-chronological-forecast-records.json --output /tmp/uf1cash-skill-report.json
```

The skill audit accepts `UF1CASH_BINARY_FORECAST_AUDIT_INPUT_V1` with records carrying `eventId`, `sport`, `marketId`, `selectionId`, pre-event `predictedAtUTC` and `modelProbability`, post-event `resultObservedUTC`, definite `outcome` (0 or 1) with `resultStatus: FINAL_REVIEWED`, `modelSnapshotUrl`, `modelSha256`, `resultSourceUrl`, and optional `baselineProbability`.

The simulation accepts only `mode: SYNTHETIC_ONLY`, the current balance, target, seed, trial count and 1–30 rounds. Each round requires unique ticket IDs with non-zero positive weights and an exhaustive **joint probability distribution** over explicit gross payout multipliers for all tickets. It rejects probabilities not summing exactly to one and cannot guess correlations.

## Security and decision rules

No real betting APIs or transfers. No source-token leakage. No synthetic bet is ever published as an actual pre-event prediction. No bankroll top-up, no automatic change to the challenge before the **R25,000** threshold, and after reaching it any new strategy requires direct user approval. Published official wallet stays at R3,071.74 until legitimate separately recorded settlements update it.
