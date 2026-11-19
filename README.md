# J$A // UFCash Public Worker

A dedicated **R0-infrastructure**, open-source-only UFC research, quality-control, and reproducible model-evaluation repository, independent of J$A's private bankroll ledger and other ventures.

## Current working provenance

- Original trained model: [SolvAI/ufcash](https://github.com/SolvAI/ufcash) at commit `c6b1e8233b172fde6e2dabb8757d351c1a4a5ede` (upstream MIT terms).
- Earlier verified research run: [GitHub Actions 44607768706](https://github.com/jakalsalfa319/AI-auto-generate-video/actions/runs/44607768706), seven matchups, 2026-11-21.
- Original public-reference odds: https://jsa-ai-trading-hq.vercel.app/api/ufc-reference-odds.
- Public J$A model dashboard: https://jsa-ai-trading-hq.vercel.app/ufcash.html.
- **Price limitation:** UFC.com public-display reference odds, neither verified bookmaker opening odds nor executable bet quotes.
- **No betting execution**, no bookmaker credentials, no payment/credits/subscriptions, and no personal financial records in this repository.

## Research architecture

1. **UFCash** runs as the trained upstream model in an isolated GitHub Actions public runner using a pinned upstream commit.
2. **Independent challengers**, including a chronological Elo model and original pre-fight statistical models, must first pass a shared leakage-free evaluation protocol before deployment.
3. **Historical validation:** sealed chronological holdouts, no post-fight information, deduplicated matchups, pre-fight fighter-name resolution, calibration and source provenance.
4. **Event checks:** public UFC pages and [ufc-cal](https://github.com/clarencechaan/ufc-cal) may offer independent schedule references, but a mention is not a confirmed completed bout.
5. **Financial validation:** calculate profit only against correctly timestamped, independently verifiable executable odds, with costs, missing markets and sample exclusions disclosed.

The 12 user-supplied candidate repositories were individually reviewed for license, role, freshness and data-leakage risk in [sources/audit.json](sources/audit.json). Listing a repository is not a license to copy its code or redistribute its datasets.

## Verified November 19, 2026 benchmark

The third odds-free model [ran successfully](https://github.com/jakalsalfa319/jsa-ufcash-public-worker/actions/runs/44616691072) using fixed training (2012-2023), 2024 validation and **untouched 2025-2026 retrospective holdout**.

| Same eligible 551 test fights | Accuracy |
|---|---:|
| Pre-fight Elo baseline | 308/551 = **55.90%** |
| New feature-based ML model | 347/551 = **62.98%** |
| Higher-confidence model selections only | 101/141 = **71.63%**, **25.6% coverage** |

The 75% confidence threshold was selected using 2024 validation only. The selected 2025 set was **57/72 (79.17%)**, but in 2026 it was only **44/69 (63.77%)**. This potential drift is a blocking research concern, not proof of stable profitability or anything close to 99.9% accuracy. None of the seven Qatar matchups passes the frozen threshold.

Machine-readable verified output: [public/precision-lab-summary.json](public/precision-lab-summary.json). The full source-data report, predictions and hashes are available in the [successful GitHub Actions artifact](https://github.com/jakalsalfa319/jsa-ufcash-public-worker/actions/runs/44616691072). Live read-only review: https://jsa-ai-trading-hq.vercel.app/precision.html.

## Precision Lab: time-separated third challenger

**Actual source:** [scripts/precision_lab.py](scripts/precision_lab.py), with [independent tests](tests/test_precision_lab.py). The workflow executes this only after UFCash has built its public pre-fight feature table.

- **Train** on eligible 2012–2023 UFC bouts using pre-fight fighter form, striking, grappling and rating evidence, never fight winners, future attributes, market odds or fighter identity as predictive features.
- **Model selection and Platt calibration:** 2024 data **only**, with predefined candidate logistic and constrained histogram-gradient boosting models.
- **Confidence / abstention policy:** threshold selected on 2024 alone to maximize the lower confidence bound subject to at least 25 accepted cases and 8% coverage.
- **Locked test:** 2025 through 18 November 2026. No parameters or thresholds chosen from this result. Report full-coverage and selected-bout accuracies, confidence interval, Brier, log loss and acceptance coverage.
- **Prospective-event research:** snapshot predicts the seven verified Qatar bouts with the model frozen at the 2023 training cutoff and 2024 calibration, not with secretly re-trained post-test parameters.

A high selected-bout hit rate alongside tiny coverage **does not** demonstrate 99.9% ability across UFC fights; never claim independently validated betting profitability without recorded executable prices and authentic settlements. Inference may improve prediction research without improving expected betting return.

## The 99.9% ambition

**99.9% is an aspiration, not an achieved or promised fight-winner accuracy.** The system must disclose: accuracy, lower 95% Wilson confidence bound, abstention/coverage, Brier, log loss, expected calibration error, sample size, drawdowns and net ROI if independently verified executable prices exist. A threshold tuned on the same test set is invalid. Claiming 99.9% only becomes defensible after independent, locked, prospective evaluation on enough fights to support the precision claim.

For selective predictions, coverage must be reported alongside precision. Abstaining from difficult matchups is not equivalent to predicting them correctly. Models may improve research usefulness without guaranteeing profit.

## Operation

The workflow `.github/workflows/jsa-ufcash.yml` is intended for **standard public GitHub-hosted runners**, with read-only repository permission, no secrets and an ephemeral environment. The event-specific input is deliberately verified against the 2026-11-21 Qatar card. Do not generalize that historical snapshot into arbitrary future cards. A future general-purpose card input interface must include public fixture validation and event-date safeguards.

The worker downloads public MMA datasets and their source content may evolve; checksums are recorded in the run provenance. UFCash uses Python `joblib` for its serialized model; loading it is potentially code-executing, so keep it on ephemeral isolated runners without credentials. No private data, credentials or account tokens should be passed.

## Licensing

This repository stores independently authored workflow wrapper/documentation and public research *metadata*. No source code from unlicensed/GPL projects is copied into a different-licensed module. Each upstream repo's code and datasets retain their respective rights; review site terms before production redistribution or commercial use.
