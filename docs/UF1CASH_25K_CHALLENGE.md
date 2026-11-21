# UF1Cash locked R25,000 virtual challenge

Approved 22 November 2026. This document supersedes previous challenges on staking size and target.

The virtual challenge began with R2,000. The user explicitly adopted the retrospective Qatar four-selection basket as the running account. The working available virtual wallet is currently R3,071.74, with the initial R500 Teixeira selection disputed and excluded from the available cash. Historical selection and price evidence is not independently authenticated as actual pre-event tickets.

**Every qualifying round, without exception before the R25,000 milestone, must stake precisely the entire current available ZAR balance.** One selection or a basket may be used, and its combined stakes must equal the available balance down to the last cent. The previous R2,000 is never reused as the stake amount. Pending stakes do not count as available. No deposits, top-ups, real money, debt, bookmaker accounts or automated real bets.

A round with no verified pre-event model forecast and fresh attributable market quote is an ABSTAIN, leaving the virtual balance untouched. Do not manufacture bets just to satisfy the full-staking rule. Only UFC and Formula 1 are active. UFC 75% / F1 25% is a research-time split, not a forced cash-stake split.

**Do not suggest a replacement or different overall challenge strategy until the available virtual balance reaches at least R25,000.** Meeting that threshold only permits a user discussion. Nothing switches automatically, and the user must approve any subsequent changes. Bankruptcy at R0 and no outstanding possible refunds ends the challenge; do not replenish virtual funds.

Continue timestamped forward trials. The adopted historical Qatar credit remains disclosed as a retrospective what-if. Preserve old forecasts and snapshots; append separately source-audited settlements. The two opposed sources for Gaziev vs Teixeira have not been reconciled sufficiently to credit the R500 leg.

## Reproducible rules

Current status:
python -m scripts.uf1cash_challenge state --wallet public/uf1cash-status.json --policy records/uf1cash/challenge-policy-v3.json --output /tmp/uf1cash-goal.json

Eligible pre-event input:
python -m scripts.uf1cash_challenge prepare --wallet public/uf1cash-status.json --policy records/uf1cash/challenge-policy-v3.json --input /path/to/verified-future-input.json --output /path/to/new-paper-receipt.json

The program refuses to overwrite a saved status/receipt, blocks stale balances and non-UFC/F1 picks, and uses the existing strict all-in paper engine. This alone cannot authenticate bookmaker quotes or source timestamps.
