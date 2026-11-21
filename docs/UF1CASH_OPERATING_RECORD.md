# J$A // UF1Cash | Virtual ZAR challenge & research ledger

**Latest user-approved sports scope (22 Nov 2026):** UFC 50%; F1, rugby union, horse racing and cricket 12.5% each of research focus. The full-wallet all-in rule and R25,000 milestone remain unchanged. Rugby/horse markets are validation adapters only; cricket is being added as an explicitly pre-event T20 market. No automatic bet without model and fresh quotes. Older 75/25 passages below are superseded historical notes.

**Current governing rule:** The R25,000 virtual challenge supersedes older examples below. Every qualifying round uses the full current available balance (currently R3,071.74), and only at R25,000 may a replacement challenge strategy be discussed, with approval required. See [locked milestone policy](UF1CASH_25K_CHALLENGE.md). The user adopted the Qatar retrospective basket into the working wallet, without claiming actual pre-event bet execution.


**Brand:** UF1Cash 🥊🏎️. The existing `jsa-ufcash-public-worker` repository, original UFCash model, immutable event prediction journals, source model checkpoints and prior test workflows remain intact. This is a brand/policy and ledger extension, *not* a covert model change or repo rename.

**As of the source review at 2026-11-21 22:32:50 UTC (00:32:50 SAST, 22 November 2026).** Recheck result sources before treating disputed outcomes as completed. Summary: [`public/uf1cash-status.json`](../public/uf1cash-status.json); evidence: [`research/uf1cash-qatar-2026-11-21-evidence-v1.json`](../research/uf1cash-qatar-2026-11-21-evidence-v1.json).

## Two deliberately separate accounting books

**Book A, genuine prospective R2,000 challenge (ACTIVE, ZERO VIRTUAL BETS):** The untouched [`genesis`](../public/ufcash-r2000-allin-genesis.json) begins with **R2,000.00 virtual available, R0.00 committed, zero pre-event paper decisions, R0.00 real money**. It carries the user's 100%-deployment requirement: when at least one eligible future event has a trusted pre-event model probability and sufficiently timely, attributable public price, allocate **the entire available round bankroll**, single or basket, to the last cent. Otherwise **ABSTAIN**. All unresolved bets lock the round; no top-ups after bankruptcy. A pre-event publication timestamp and the underlying genuine quote/feature provenance must both be verified before crediting performance. No automatic bookmaker interaction. The existing [`scripts/all_in_challenge.py`](../scripts/all_in_challenge.py) performs the accounting.

**Book B, retrospective UFC Qatar, 21 November 2026 (ARCHIVED WHAT-IF ONLY):** The user's historical counterfactual scenarios use original forecasts saved before the event and prices *reported later* by a 19 November third-party account of a BetOnline board. The **3% hypothetical EV threshold** and **all-in allocation rule** were chosen after the event, so these results are not independently precommitted paper wagers. Prices are not authenticated bookmaker offers. Book B is *not funded by* or credited into Book A. Two mutually exclusive examples cannot be added together.

| Historical what-if | Imaginary committed | If Gaziev–Teixeira settles against Teixeira | If Gaziev–Teixeira settles for Teixeira |
|---|---:|---:|---:|
| Four-bet basket: R500 on Stirling, Aliskerov, Luna, Teixeira | R2,000 | R3,071.74 balance (+R1,071.74) | R4,396.74 balance (+R2,396.74) |
| Single maximum-model-EV case: R2,000 on Teixeira | R2,000 | R0.00 (-R2,000.00) | R5,300.00 (+R3,300.00) |

For the basket, Stirling returned **R779.33** gross, Aliskerov **R672.41**, and Luna **R1,620.00** on the post-hoc R500 stake selections, summing to **R3,071.74**. Teixeira's R500 was not settled, and its possible gross return is R0.00 or R1,325.00. There is no *verified realized* win/loss on the historical stakes: **these are conditional arithmetic from reported odds and fight reports**, not previously placed orders.

The original UFCash winner probabilities picked **5 of 6** non-disputed reported winners (83.33%). The available favourite baseline also picked 5/6 on the same sample. **Gaziev–Teixeira remains DISPUTED**: [MMA Fighting's live result](https://www.mmafighting.com/ufc/522605/ufc-qatar-results-prochazka-vs-stirling) reports Teixeira, while a [UFC-hosted official-scorecards page](https://us.ufcespanol.com/news/ufc-qatar-official-scorecards-prochazka-vs-stirling) explicitly reports Gaziev. An official UFCStats completed-fight detail with independently checked fighter statuses is not yet in our evidence. A subsequent verified correction must be added as a **new versioned review**; never silently rewrite the original frozen forecasts or this audit trail.

Historical quoted prices: [Garcia Report, 19 Nov](https://www.thegarciareport.com/posts/ufc-qatar-prochazka-stirling-betonline-moneylines/). No claim about actual availability to a South African user.

## Strict development split, no automatic cash split

- **75% UFC:** Continue independent prospectively frozen model predictions, two-sided market analysis, pre-event price snapshots, completeness and bout-identity checks, leakage audits, prospective Brier/accuracy and a same-market bookmaker/favourite/no-bet comparison. Existing model probabilities are not automatically calibrated betting value.
- **25% Formula 1:** Keep read-only Jolpica race-calendar intake and build a genuinely evaluated F1 race-market model. As of 22 November, the official F1 calendar shows **Qatar Grand Prix 27–29 November** and **Abu Dhabi Grand Prix 4–6 December 2026**. A race calendar is not odds, an accurate probability, or a qualifying all-in paper selection. No F1 bet can be invented to meet a target ratio.
- **Bench ON HOLD:** Rugby union, horse racing, cricket, tennis, basketball, football and other motorsports remain preserved for review only. Do not delete working code or begin new active integrations/automated bets on those sports until UFC **and** F1 have sufficient forward evidence of accurate sourcing, reproducible forecasts, baseline outperformance and meaningful measured virtual returns. No shortcut or assumed profitability milestone.

The percentages are **effort and development priorities, not guaranteed portions of R2,000 bankroll**. The full imaginary bankroll remains governed by the independent all-in eligibility/abstention rule. There can be rounds only in UFC, only in F1, or both if legitimately qualified. With missing evidence the correct decision is *no round*.

## Controls and evidence required for genuine success

1. An independent timestamp of **pre-event** source probabilities, model version/SHA and actual eligible fixtures. No after-the-fact selection, model training, rule tuning or hindsight labels.
2. Attributable and timestamped two-sided market prices, with stale/unavailable or unsupported markets rejected. Public quotes do not prove availability to place a real wager.
3. After the event, independently inspect official result content and settlement rules; do not accept a URL alone or call a disputed win a profit.
4. Compare to no-bet, same-quote market favourite and plausible market-implied-probability baselines, reporting sample size, Brier, log loss, ROI scenarios, drawdowns and bankruptcy risk. A positive post-hoc profit does not constitute success.
5. Only consider the sports proven when repeated forward out-of-sample assessments produce measurable performance with uncertainty intervals. The 100%-exposure rule is intentionally aggressive; bankruptcy is a valid outcome and must not be erased or topped up.

## Reproduce without internet or betting access

```bash
python -m scripts.uf1cash_status --output /tmp/uf1cash-rebuilt.json
python -m unittest discover -s tests -p 'test_uf1cash_status.py' -v
cmp /tmp/uf1cash-rebuilt.json public/uf1cash-status.json
```

No real wagers, private credentials, payments, automatic bookmaker access, or betting advice execution is provided here.


## 22 November 2026: user-directed retroactive virtual balance rollover (v2)

The user explicitly instructed UF1Cash to use the **four virtual R500 Qatar bets as the working R2,000 challenge**, crediting the three reported winning returns to the live virtual balance. This is a CHANGE IN HYPOTHETICAL ACCOUNTING POLICY on 22 November, not evidence of an actual bet or an earlier frozen paper order.

The current working virtual balance is **R3,071.74**: starting R2,000.00, less four R500 historical simulated stakes, plus R3,071.74 reported gross payouts. The final R500 simulated stake on Tallison Teixeira remains disputed and is **already deducted**, so no additional payout has been credited. A verified win under the historical reported price could add R1,325.00 gross (bringing the account to R4,396.74). A loss adds nothing. The displayed scenario profit is +R1,071.74 relative to original virtual opening capital, **not proven real or prospective profit**.

The previous v1 summary is archived at [status-snapshot-v1.json](../records/uf1cash/status-snapshot-v1.json), the author's decision is recorded in [wallet-rollover-authorization-v2.json](../records/uf1cash/wallet-rollover-authorization-v2.json), and the generator now creates [v2 live status](../public/uf1cash-status.json). The original model forecasts, genesis record and v1 evidence review are untouched.

**Future model-qualified round policy:** deploy all of the **currently available** R3,071.74 only to a genuine pre-event research decision. The unresolved old R500 stake is not available for reuse. No top-ups. Development remains 75% UFC / 25% F1; all other sports benched.
