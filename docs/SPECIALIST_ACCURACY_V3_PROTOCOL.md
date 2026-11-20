# J$A Specialist Accuracy Lab v3 (research-only)

## What this actually tests

The prior J$A model, Frontier v2, recorded **176/266 (66.17%)** correct historical 2026 winners with a 2025-selected 65% confidence gate. Its confidence interval for improvement over the frozen baseline includes zero, and the 2026 results have already been inspected. The goal of v3 is therefore **not** to claim another clean holdout: it is to ask whether pre-fight fighter traits and disagreement among previously trained experts justify a small, reproducible probability correction.

Source:
- [scripts/frontier_specialists.py](../scripts/frontier_specialists.py): 10-feature **residual logistic coach** added to the **frozen** Frontier v2 log-odds. All corrected probabilities reduce to Frontier v2 when residual weights are zero.
- [scripts/accuracy_frontier.py](../scripts/accuracy_frontier.py): exports additional **historical pre-fight** striking differential, takedowns, takedown defense, control, previous UFC fight counts, and days since the prior fight in audit-only case records.
- [tests/test_frontier_specialists.py](../tests/test_frontier_specialists.py): verifies corner-swap antisymmetry, no wrong-year fitting, regularized stable training, and that changing any 2026 outcomes cannot change the 2025 go/no-go decision.

## Exact data split

- Fit original v2 experts on **2012–2024**; calibrate on **January–June 2025**.
- Fit the new **specialist residuals on July–September 2025** only.
- Require the predeclared October–December 2025 check to improve Brier score by at least **0.001** without decreasing winner accuracy by more than **2 percentage points**.
- If the 2025 check passes, refit the same strongly regularized residual on **all July–December 2025** for the *diagnostic* 2026 replay. If it fails, the script returns **exactly the original Frontier v2 predictions**.
- Score 2026 on the **same eligible 266 completed fights**, including Q1–Q4 and fixed-65%-threshold coverage. No 2026 labels enter coefficient fitting, rule selection or calibration. 2026 is a *development replay*, not an untouched holdout.

**Frozen coefficients/settings before inspecting new scores:** residual L2 coefficient `0.12`, fixed 10 features, no intercept, fixed 65% selective confidence rule, deterministic Newton optimization, and fixed 2025 Q3/Q4 validation gate. Features are antisymmetric when fighter corners swap: `f(-x)=-f(x)`, so the corrected model preserves complementary win probabilities.

## How success must be assessed

The generated `results/specialist_lab_v3.json` must show the 2025 validation outcome, complete and selected 2026 sample sizes, winner accuracy, Brier, calibration error, quarter-level results, and an event-clustered paired interval against Frontier v2. A higher percentage from a tiny subset is not a full-coverage accuracy improvement. Confidence intervals that cross zero are inconclusive.

**No automatic promotion to production.** The specialist is a separate experimental report and does not change the locked pre-event 21 November predictions or the J$A website, financing records, sportsbooks or real betting decisions. Evidence for actual improvement must be independently replicated on *new* prospective UFC events after the experiment is locked.

## Accuracy and profitability are different

The 70% full-fight and 80% selective targets are exploratory milestones, not forecasts. Neither retrospective performance nor a percentage-probability estimate proves that a bookmaker price offers positive expected value. There are no live executable odds, actual wagers, payments, profitability claims, or paid cloud services in this research path.

## Cost and provenance

Standard free GitHub Actions public repository runner, existing pinned SolvAI/ufcash revision, NumPy and scikit-learn installed in the original job. No paid API credits, subscriptions, or new Vercel functions.
