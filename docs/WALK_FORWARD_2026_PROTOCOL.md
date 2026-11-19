# 2026 Walk-forward accuracy experiment

**Status:** source, regression guards, CI and journal are implemented. This document is the fixed evaluation policy, not a claim of model superiority.

## 2026 chronological replay

The [rolling 2026 worker](../scripts/rolling_2026.py) fixes all four model families and their hyperparameters in source: `logistic_weak`, `hist_boost`, `xgboost`, `catboost`. It never uses odds, results, fight names, identities or data recorded after the prediction date as model features. For each quarter:

| Prediction period | Training observations strictly before | Model-selection + calibration observations |
|---|---|---|
| 2026 Jan–Mar | 2025-10-01 | 2025 Oct–Dec |
| 2026 Apr–Jun | 2026-01-01 | 2026 Jan–Mar |
| 2026 Jul–Sep | 2026-04-01 | 2026 Apr–Jun |
| 2026 Oct–18 Nov | 2026-07-01 | 2026 Jul–Sep |

The four predefined candidates are trained on the pre-calibration period. The last completed quarter's **Brier score alone** chooses the candidate; the probability recalibration is fitted using that prior quarter. The selected model is then frozen for the *next* quarter. Earlier 2026 outcomes may inform later 2026 predictions, but no current/future quarter outcome is allowed.

**Frozen selection threshold:** 75% confidence, with a separate all-eligible comparison. Both must report sample counts, coverage, accuracy, Brier, log loss, ECE, and 95% Wilson bounds. Compare the exact same fights against the **frozen 2023-trained/2024-calibrated** model and `p_elo32`. Report the four candidate families for **diagnostic** purposes only; do not retroactively choose the one with the best 2026 score.

A paired bootstrap samples whole UFC event dates to estimate an exploratory interval for the rolling-vs-frozen accuracy difference. It is not an independent significance test and is not evidence of guaranteed edge.

## Evidence limitations

**2026 has already been inspected during project development.** Consequently this is a retrospective **development** replay, *not* a new untouched test. Source data may be revised by original maintainers. Upstream UFCash generates date-batched features, but independent historical point-in-time source verification remains pending.

The earliest fully prospective benchmark starts only from predictions timestamped and frozen **before** future fights, independent result feeds later. More accurate winner prediction does not automatically create positive ROI: executable source-identified bookmaker prices, proper stakes and settlement histories are separate prerequisites. No wagering execution or paid service is used.

## Prospective evidence journaling

The [journal script](../scripts/prospective_journal.py) writes a read-only forecast snapshot with event date, UTC creation time, exact fighter pairs, model probabilities, frozen confidence status and source SHA-256 hashes. It **refuses to backdate** a snapshot once the event date has begun in UTC. GitHub Actions retains the timestamped research bundle for **30 days**. This is not permanent cryptographic notarization: archive the artifact if retention must exceed that window.

After the event ends, [settle_prospective.py](../scripts/settle_prospective.py) can score independent results only when an externally supplied completed-results CSV includes both fighters, source URL, outcome and verification timestamp. It checks the original journal digest and never rewrites that journal. Draws/no-contests are excluded from decisive accuracy; no ROI is computed without verifiable executable odds.

## R0 resources and rights

Public GitHub Actions runner, pinned UFCash sources and free repository artifacts. No paid API keys, software subscriptions, sportsbook credentials, bank details or financial records are placed in the public repository.

**Release gate:** A retrospective improvement can be marked *experimental* only. Never promote it to a "99.9% accuracy" claim or auto-betting strategy without enough independent prospective evidence and proof of economic value.
