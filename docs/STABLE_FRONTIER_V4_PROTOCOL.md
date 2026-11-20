# Frontier Stable v4: reproducible ensemble experiment

**Status:** predeclared reproducibility experiment; outcomes must be read from successful GitHub Actions artifact before asserting gains. Existing Frontier v2 research and pre-event journal are unchanged.

## Why this is necessary

The original Frontier v2 (40% regularized logistic, 20% scikit-learn histogram boosting, 20% XGBoost, 20% CatBoost) recorded **176/266 historical 2026 winners** in its archived 20 November run. A later fresh run with the **same nine UFC raw-source SHA-256 fingerprints and the same 266 fight identifiers** reported **175/266**. Comparing its per-fight outputs revealed a single correct/wrong flip around the 0.5 decision boundary, while most probability changes were smaller than one percentage point.

Two runs with single-thread model and BLAS execution proved that XGBoost and CatBoost prediction hashes were **identical**, and logistic outputs were stable to practical precision. The histogram-boosting probability hashes were **not identical** and were the principal source of ensemble variation. The source and original result are preserved. Single-threading alone did not eliminate the scikit histogram-boosting variation.

## Frozen alternative

[Frontier Stable v4](../scripts/stable_frontier_v4.py) tests fixed weights:

| Source model | Weight |
|---|---:|
| 2012–2024 trained and 2025-calibrated logistic | 40% |
| XGBoost, fixed-seed, one CPU thread | 30% |
| CatBoost, fixed-seed, one CPU thread | 30% |
| Histogram booster | **0%** |

The underlying input data are the **same exact 2012–2024 pre-fight training data**. New code exports aligned component probabilities for calendar **2025 H1**, **2025 H2** and **2026 through 18 November** from the existing Frontier training run. A **single symmetric Platt slope is fitted on 2025 H1 only**. No weights are selected using 2026 scores.

### Locked 2025 validation gate

Evaluate all 146 eligible July–December 2025 matches on the same fight identifiers and outcomes as the original ensemble. Stable v4 must improve Brier score by at least **0.001**, with no more than **2 percentage points** reduction in winner accuracy, to pass this fixed gate.

Regardless of pass/fail, record the full **266-fight historical 2026 diagnostic** plus a fixed 65% confidence-coverage comparison, an event-clustered paired accuracy interval and independent per-component probability hashes. Do not silently promote the new model based on retrospective 2026 results. If the 2025 gate fails, treat the alternative as **rejected for promotion**.

## Reproducibility tests

Run the complete worker with the same pinned UFCash commit, source checksums and dependency versions. Compare **fingerprints of the three model components and 8-decimal stable-ensemble outputs** between independent runs. A reproducibility pass requires matching fight IDs, training source hashes and probability fingerprints, not merely identical headline winner accuracy.

**Important limitations:** The 2026 cohort has already been examined and is not a fresh sealed prospective test. Source revisions and unknown future cards can still affect live prediction performance. No sportsbook prices, wagering actions, financial returns or 99.9% prediction claim are supported by this experiment.

## R0 stack and preservation

The experiment uses the existing free GitHub Actions public runner and pinned upstream open-source model dependencies. It adds no paid API or hosted service. The J$A website, Finance data and both frozen November 21 pre-event forecast journals remain unchanged until independently validated future work authorizes a new version.
