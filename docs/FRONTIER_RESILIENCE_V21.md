# J$A Accuracy Frontier v2.1: fighter-history and drift diagnostics

**Status:** Reproducible research enhancement to the existing Frontier v2 model. Do not replace or retrain the public v2 predictions because the historical 2026 outcomes have already been examined.

## Source of truth

- Trained model: [accuracy_frontier.py](../scripts/accuracy_frontier.py) and the previously verified [Frontier v2 run](https://github.com/jakalsalfa319/jsa-ufcash-public-worker/actions/runs/44754660814).
- The model now exports **audit-only** records `results/frontier_cases.json`: the original version's five candidate probabilities, timestamped historical outcome, both fighters' previous UFC fight counts, and days since their previous fight. This does not change fitting, prediction, family selection, probability calibration or the frozen 21 November forecasts.
- The independent [frontier_resilience.py](../scripts/frontier_resilience.py) audits historical records against **five rules fixed in code before selection**: the original 65% gate; 70% confidence with ≥5 prior fights on both sides; 65% confidence with ≤15pp dispersion and unanimous model side; 65% with ≥5 prior fights and ≤18pp dispersion; and 70% confidence with both fighters' most recent bouts ≤540 days ago.

## Chronology and scoring

The original Frontier model's **family and calibration** use up to 2025 H2; its regression fit excludes 2026. Resilience filter selection uses **only July–December 2025** outcomes, maximizing the one-sided Wilson lower bound subject to at least **30 accepted fights** and at least **20% coverage**. Every rule, including the losing alternatives, is then scored on the same previously examined 2026 results. We also show Q1–Q4 as **descriptive diagnostics only**, including overlapping groups with low history, long layoff, low confidence and large disagreement.

Do not use 2026 Q4 results to pick a new cutoff or claim the best-performing subset is independent. These results are a **development-period replay**, not prospective evidence. Selecting another policy after seeing the 2026 scores would invalidate any estimate of generalization.

The chosen risk rule must report selected count, eligible fights, precision, Wilson confidence bound, Brier, frozen-model accuracy *on the same selected subset*, and how many bouts it abstained from. A 100% rate on a few fights does not count as 99.9% verified accuracy.

## Promotion gate

The analysis always returns `NO AUTOMATIC POLICY PROMOTION`. No commercial live betting recommendations or bookmaker integrations follow directly from a retrospective filter. The next scientifically defensible improvement is locking the risk policy **before a new event**, preserving its model probabilities, and verifying results from independent official sources later.

## Infrastructure and rights

Public read-only source data, GitHub Actions standard runner, free/open dependencies. No paid hosted resources, no subscriptions or credits, no automatic bets and no private bank/ledger data. The upstream historical data may include retrospective revisions, so source-as-of validation remains necessary.
