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

## Final Event Evidence workflow (20 November 2026)

**Live evidence viewer:** https://jsa-ai-trading-hq.vercel.app/event-evidence.html

The v2.1 UFC source gate and new result-audit scripts use the two immutable pre-event forecasts at `public/prospective/2026-11-21.json` and `public/prospective/2026-11-21-frontier-v2.json`. These originals are not overwritten. The archived [20 November card verification](public/card-integrity-2026-11-20.json) found **7/7 exact same-bout UFC listings**, with recorded page SHA-256 and timestamp.

**Operational checks (UTC, +2 hours for South Africa):**

- **21 Nov 09:30 UTC / 11:30 SAST:** [Official card identity recheck](.github/workflows/card-integrity.yml), which verifies the listed matchups but does not assign winners.
- **22 Nov 12:00 UTC / 14:00 SAST:** [Official UFCStats post-event audit](.github/workflows/post-event-evidence.yml).
- **23 Nov 12:00 UTC / 14:00 SAST:** Second audit for late/incomplete official results.

The [new evidence collector](scripts/verify_official_results.py) requires the exact event in UFCStats completed-event listings, then opens individual fight-details pages and checks **both exact fighter identities and their W/L/D/NC statuses** before scoring any frozen model probability. Missing sources, altered fighters, unclear status and inaccessible records remain **PENDING**. Completed fights are reconciled with all frozen models using [settle_event_v2.py](scripts/settle_event_v2.py). These findings remain **GitHub Actions artifacts only**, not automatically published as verified results or bankroll entries.

[Initial 20 November post-event workflow test](https://github.com/jakalsalfa319/jsa-ufcash-public-worker/actions/runs/44764891931) completed with **34 passing tests**; the pre-event date gate correctly skipped real results collection. The repo uses free public GitHub Actions and a static-only website viewer because the Vercel Hobby site already uses 12 serverless functions. No new paid infrastructure or wagering execution was added.

**Known limitations:** UFCStats availability, post-event structure changes, delayed/corrected results, and source provenance can all block settlement. This is intentionally fail-closed. No 99.9% winner accuracy, genuine betting profit, or final 21 November event result has yet been established.

## 21 November UFC Qatar: verified source and scoring pipeline

**Pre-event UFC same-bout check passed 7/7** at 2026-11-20 15:20 UTC. Unlike fighter-name mentions, the [official card gate](scripts/card_integrity.py) requires both original opponents within the same UFC event bout listing. [Source record](public/card-integrity-2026-11-20.json) includes the official URL, UTC observation and raw HTML SHA-256. [Successful independent GitHub run](https://github.com/jakalsalfa319/jsa-ufcash-public-worker/actions/runs/44763158863) runs **23 tests** plus card verification. The [lightweight scheduled recheck](.github/workflows/card-integrity.yml) is configured for 21 November at 09:30 UTC, without altering the historical models.

The [status-safe multi-model settlement](scripts/settle_event_v2.py) accepts official-linked completed results **after** the event, scores the unchanged [first journal](public/prospective/2026-11-21.json) and [Frontier v2 journal](public/prospective/2026-11-21-frontier-v2.json), and excludes draws, no-contests, cancelled, replaced, postponed and pending bouts. Full instructions: [Card Integrity and Settlement](docs/CARD_INTEGRITY_AND_SETTLEMENT.md). [Results intake template](templates/ufc-qatar-2026-11-21-outcomes.csv) currently marks all seven bouts **PENDING**. No results have been scored or financially settled.

**Quality principle:** An official card listing is not proof a bout ultimately happened; a provided official results URL is not proof the claimed outcome was checked against the page. Report all verification limits explicitly. Actual winner accuracy, 99.9% performance and profitability must be supported by independent prospective evidence.

## Frontier Resilience v2.1: real Q4 drift audit (20 November 2026)

**Live public viewer:** https://jsa-ai-trading-hq.vercel.app/resilience.html

The reproducible [GitHub Actions run](https://github.com/jakalsalfa319/jsa-ufcash-public-worker/actions/runs/44758648862) passed the model and risk-audit steps, including 2025-only selection of five predefined risk filters. **The 65% baseline rule remains selected. No new policy was promoted.**

- Unchanged all-fight 2026 model: **176/266 = 66.17%**.
- Preselected research-confidence rule: **103/156 = 66.03%**, **58.65% coverage**.
- Alternative stricter 70%-confidence/≥5-previous-fights rule: **52/74 = 70.27%**, only **27.8% coverage**. This was NOT selected on 2025 evidence and cannot be treated as a verified improvement.
- Q4 2026: **29/48 = 60.42%**. The subset with fewer than five recorded prior UFC fights for either fighter was **10/18 = 55.56%**. These small, overlapping groups are descriptive research, not validated risk causes.

[Complete public release summary](public/frontier-resilience-v21.json), [precommitted protocol](docs/FRONTIER_RESILIENCE_V21.md) and source code in `scripts/frontier_resilience.py`. The complete historical audit records are in the run artifact for 30 days; file hashes are published in the public summary.

**Evidence warning:** This 2026 data was already examined during project development. A 99.9% winner-accuracy claim or betting profitability remains unsupported; no actual wagers or money movement were made.

## Fitted Frontier v2 frozen for reuse (20 November 2026)

**Permanent public GitHub Release:** [J$A Frontier v2 fitted models](https://github.com/jakalsalfa319/jsa-ufcash-public-worker/releases/tag/jsa-frontier-v2-fitted-2026-11-20).

The verified [20 November source run](https://github.com/jakalsalfa319/jsa-ufcash-public-worker/actions/runs/44774744415) saved the **actual four fitted research models** (logistic, histogram boosting, XGBoost, CatBoost), 2025-H1 calibration, 2025-H2 selected 65% research-confidence gate and 50 original plus six derived feature names. Its 24-fixture restore test passed. The original nine source SHA-256 hashes matched the original data. **This newly frozen fitted snapshot scored 176/266 (66.17%) retrospectively in its own completed run.** It does NOT reconstruct the exact fitted object from the earlier v2 archived run, even though the headline score agrees.

The release permanently holds both:
- `frozen_frontier_v2_checkpoint.tar.gz` (four serialized fitted models; **SHA-256 `727b4a535927157257de84f6a7cc3fd5988aba9cabb98ba6bf84e726dc1a3a97`**).
- `frozen_frontier_v2_receipt.json` (independent hash, pinned package versions, input-source count, replay evidence).

The independent [free verification workflow](.github/workflows/verify-fitted-checkpoint.yml) **[passed on a fresh runner](https://github.com/jakalsalfa319/jsa-ufcash-public-worker/actions/runs/44775978800)**. It downloaded the published release, used pinned dependencies, verified SHA-256, reloaded the actual fitted objects and reproduced all 24 validation probabilities **without retraining**. Six further checkpoint tests passed. The maximum fighter-order complementarity deviation was 2.75×10⁻⁸, inside the documented 10⁻⁶ numerical tolerance. The independently anchored [approved model manifest](public/approved-frozen-frontier-v2.json) contains the exact SHA and tests.

**Operational usage:** [Fitted Frontier Model Checkpoint guide](docs/FITTED_FRONTIER_MODEL_CHECKPOINT.md). The `scripts/model_checkpoint.py` inference command requires an independently trusted SHA-256 and future genuinely `UPCOMING` pre-fight features, and refuses to overwrite a prediction journal. No private finances, wagers, brokerage/betting accounts, 99.9% claims, or unverified ROI are involved. This does **not** promote the model to automatic real-money betting.

## Frozen future-event research pipeline

**Approved fitted model:** [Frontier v2 permanent release](https://github.com/jakalsalfa319/jsa-ufcash-public-worker/releases/tag/jsa-frontier-v2-fitted-2026-11-20) with SHA-256 727b4a535927157257de84f6a7cc3fd5988aba9cabb98ba6bf84e726dc1a3a97. It is loaded unchanged for future predictions. No re-training or automatic bet execution is needed.

- [Draft generator](scripts/prepare_future_card.py) prepares cards/drafts/YYYY-MM-DD.json from real pre-event UFCash feature parquet, keeping missing statistics as null and preventing known-outcome leakage.
- [Reviewed card folder](cards/reviewed/README.md) separates real owner-reviewed evidence from drafts. The future inference command rejects unreviewed, stale, duplicate, past, incomplete or outcome-bearing cards.
- [SHA-pinned future inference](scripts/future_card_inference.py) enforces the 50 original features + 6 model interactions, correct UTC chronology, actual current UFC same-bout listings and the exact approved frozen release. Generated predictions contain no wins/results/bets and explicitly say the feature source has not been independently audited.
- [Free GitHub Actions workflow](.github/workflows/frozen-future-inference.yml) runs regression checks on code changes. When a verified future card is committed, use its path as the Run workflow manual input. Only the user-directed dispatch produces an expiring read-only model-report artifact.
- [Step-by-step review and run instructions](docs/FROZEN_FUTURE_INFERENCE_V1.md).

**Archived historic worker:** The older 21 November Qatar training workflow is now manual-only because the mutable upstream UFC historical database no longer matches its approved raw-data fingerprints. Existing model artifacts and both pre-event November 21 journals are preserved; the older job must not rerun automatically and silently redefine their probabilities.

**Evidence boundary:** No new actual future event has been supplied, so this system has not published a new prospective prediction. Synthetic test fighters are used only in-memory for unit testing and will never be represented as real source-verified UFC bouts. 66.17% is a historical already-examined benchmark, not a prospective guarantee or proven betting profitability.

## Model reliability audit: Specialist v3 and Stable v4 (20 November 2026)

The next two independently tested accuracy challengers were **rejected instead of deployed**, because neither passed the validation criteria fixed before scoring the 2026 data.

| Historical experiment | 2025 evidence | Historical 2026 diagnostic | Decision |
|---|---|---|---|
| **Specialist v3** (pre-fight styles, experience, inactivity) | 2025 Q4: 47/78 vs v2 50/78; worse Brier | No model promotion; original v2 retained | **Rejected** |
| **Stable v4** (40% logistic / 30% XGBoost / 30% CatBoost) | 2025 H2 Brier 0.22450 vs v2 0.22412; fails fixed gain requirement | 172/266 (64.66%) vs same-run v2 176/266 (66.17%) | **Rejected** |

**A separate reproducibility issue was discovered:** even with identical raw source hashes and fight IDs, consecutive original v2 re-trainings yielded **175/266 and 176/266**. Exact model fingerprints isolated meaningful output variation to the histogram-boosting component; XGBoost and CatBoost output hashes matched, with only negligible logistic floating-point differences. Single-threading alone was not sufficient. A one-fight accuracy fluctuation is not a verified performance improvement.

- [Complete versioned reliability audit](public/accuracy-v3-v4-reliability-audit.json)
- [Specialist v3 historical validation and rejection](public/specialist-lab-v3-rejection.json)
- [v3 method](docs/SPECIALIST_ACCURACY_V3_PROTOCOL.md)
- [v4 reproducibility method](docs/STABLE_FRONTIER_V4_PROTOCOL.md)
- [Successful v4 worker run with reproducibility evidence](https://github.com/jakalsalfa319/jsa-ufcash-public-worker/actions/runs/44770722895)

**Research policy:** retain the archived v2 release as an explicitly run-specific result, preserve the two immutable pre-event forecasts, and fix model reproducibility before making new claims. Future fitted models should be versioned and frozen; truly new fights must supply prospective verification. None of this demonstrates 99.9% accuracy, bookmaker profitability or authorizes betting execution.

## Current verified research release: Accuracy Frontier v2 (20 November 2026)

**Live read-only dashboard:** https://jsa-ai-trading-hq.vercel.app/frontier.html

The 2025-selected **nonlinear ensemble** (40% logistic, 20% histogram boosting, 20% XGBoost and 20% CatBoost), trained on pre-fight statistics with symmetric matchup features, produced the following results on **exactly the same 266 completed 2026 fights**:

| 2026 winner model | Correct / eligible | Accuracy | Brier |
|---|---:|---:|---:|
| Historical Elo32 | 146 / 266 | 54.89% | 0.2459 |
| Frozen first-generation logistic | 167 / 266 | 62.78% | 0.2401 |
| **Accuracy Frontier v2** | **176 / 266** | **66.17%** | **0.2306** |

**Nine additional correct outcomes**, an improvement of **3.38 percentage points**. A 2025-selected 65%-model-confidence rule scored 103/156 selected fights (66.03%) with 58.65% coverage; this is not a universal 66%-accuracy guarantee. Its validation-only accuracy was 54/75 (72%) and the 2026 accuracy was lower. The event-clustered 95% interval for the overall accuracy change was **−0.399 to +7.20 percentage points**; it crosses zero.

**Important evidence boundary:** 2026 was already examined during this project's development, so this is retrospective development evidence, **not an independent prospective test**, verified betting edge, or support for a 99.9% win claim. A weakening in Q4 2026 further warrants drift monitoring. We have **not** switched on automatic wagering or made actual bets.

- [Successful GitHub model run](https://github.com/jakalsalfa319/jsa-ufcash-public-worker/actions/runs/44754660814)
- [Versioned research results](public/accuracy-frontier-v2.json) with hashes and cohort counts
- [Model code](scripts/accuracy_frontier.py) and [predeclared research protocol](docs/ACCURACY_FRONTIER_V2.md)
- [Pre-event 21 November version-2 research forecasts](public/prospective/2026-11-21-frontier-v2.json). These were recorded on 20 November; outcomes are left unknown.

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
