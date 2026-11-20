# Accuracy Frontier v2

## Aim

Test a **predeclared** improvement over the previously verified ~62.8% all-fight 2026 model performance without changing any existing published model or result. The long-range 99.9% objective is aspirational and not implied by this experiment.

## Chronological design, frozen 20 November 2026

| Stage | Fights used | Permitted use |
|---|---|---|
| Historical fixed comparator | 2012–2023 | Train frozen weak-regularization logistic |
| Historical comparator calibration | 2024 | Calibrate frozen comparator |
| Contemporary training | 2012–2024 | Fit predeclared candidate models |
| Contemporary calibration | January–June 2025 | Calibrate candidates with symmetric Platt slopes |
| Model family and confidence selection | July–December 2025 | Choose lowest Brier family, then maximize confidence-bound accuracy with ≥35 accepted and ≥20% coverage |
| Development-period replay | January–18 November 2026 | Measure same-fight accuracy, Brier, log loss, 10-bin ECE, selected precision/coverage, quarterly stability and paired event-clustered accuracy difference |

**2026 is not an independently sealed holdout.** Previous versions were examined using these fights, so this new set is diagnostic development evidence only. No family, threshold, weight or feature is adjusted after checking 2026 scores.

## Predeclared model family candidates

- `frozen_v1`: previous weak-regularization logistic model, 2023 training cutoff, 2024 calibration.
- `recent_logistic`: current same-family logistic model trained through 2024 with six antisymmetric matchup interaction features.
- `time_decay_logistic`: as above but older fight weights decrease with a fixed four-year half-life, minimum weight .12.
- `nonlinear_ensemble`: fixed 40% logistic + 20% HistGradientBoosting + 20% XGBoost + 20% CatBoost, with no test-informed weight tuning.
- `elo_blend`: fixed 80% recent logistic + 20% independent pre-event Elo32 probability.

New cross-feature interactions are odd under swapping fighter corners: `f(-X)=-f(X)`. They combine striking, grappling, control, quality of opponents, pace and defensive profile. No odds, fighter identity, post-fight outcome or physical-fighter height/reach imputations enter the predictors.

The family-selection objective is **2025 H2 Brier score** to avoid overconfidence. The confidence cutoff is selected **only in 2025 H2** on a fixed grid between 50% and 85%; Wilson lower-bound selection requires a meaningful minimum coverage/sample. Every eligible completed 2026 fight remains in the full-coverage comparison even when the confidence gate abstains.

## Evaluation protocol

Read `scripts/accuracy_frontier.py` and `tests/test_accuracy_frontier.py`. The workflow must produce `results/accuracy_frontier_2026.json`, explicitly label any 2026 all-family scores as *diagnostics not for selecting families*, and include a list of unscored pre-event forecasts with no result labels. The old v1.6 and v1.7 website pages and primary worker remain untouched by this study.

**Operational promotion gate:** No replacement of the proven baseline merely because an exploratory 2026 score looks larger. Require prospective fights after the code is locked and source as-of audit before claiming a real improvement. A high hit rate doesn't establish a betting ROI without source-identified executable bookmaker odds and costs.

## R0 policy

Public GitHub-hosted runner, pinned UFCash data preparation, Python open-source libraries, no paid compute, API credits, subscriptions, private finances, automated wagers or brokerage connections. Source datasets and code retain the original authors' licenses.
