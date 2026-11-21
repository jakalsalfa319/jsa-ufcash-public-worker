# UFCash / J$A: R2,000 all-in virtual challenge v1

Status: **R0 fictional-money simulation**. No deposits, actual bets, bookmaker logins, automated execution, debt, credit or top-up. First genuine future all-in decision has **not** been frozen yet.

## Locked rules

1. Virtual opening bankroll: **R2,000.00**. No replenishment. Any future virtual winnings become the full opening balance of the next round.
2. **Every active round spends exactly 100.00% of that round's available ZAR balance**, leaving **R0.00 uncommitted**. Exactly one side for **SINGLE**; multiple distinct events for **BASKET**, their allocated stakes adding to 100% down to the last cent. Simultaneous bets form one round. Do not roll winnings from one event into a different event that began before the first result was available.
3. A completely losing round or single loss puts bankroll at R0 and ends the challenge. The bank cannot become negative. Pending/disputed selections mean round not closed and **zero capital may be used for the next round**.
4. Screen only *actual* pre-event model predictions and identified pre-event public quote observations. Model-conditional estimated EV = `p * decimal_odds - 1`. 3% is an exploratory threshold carried from prior work; **it does not prove real edge**. Missing, old, ambiguous, unsupported or invalid quotes cause no bet. A round without a qualifying selection **abstains**, holding the bankroll until a later opportunity.
5. For forward rounds, `scripts/all_in_challenge.py` accepts a genuine model source URL and a 64-character SHA-256 fingerprint, event/quote/forecast timestamps, selection, market, odds and an attributable source. A SHA verifies the receipt's byte consistency; it **does not prove** a claimed earlier observation truly occurred then. Publish the source and the receipt via independently dated GitHub Actions BEFORE the event for a real paper-trial classification.
6. A source URL for the result alone is not proof of the winner. `settle_round` always describes claimed results as **provisional**, never independently audited or confirmed executable quotes. Missing/disputed event statuses remain unsettled. Only use final official results and a source-content audit for prospective proof.
7. No enhancements are promoted on the basis of already observed winners or after-event market selection. Compare performance to identical no-bet, market favourite and random/baseline strategies with the same fully exposed simulated ZAR. Track time, quote staleness, coverage, wins, bankruptcies, drawdown, calibration and the fraction of goals achieved.

## Reproduced historical scenario, Qatar 21 Nov 2026

Input: `research/2026-11-21-qatar-reference-input.json`, frozen pre-event UFCash prediction journal and a *later-discovered* article describing 19 November odds. **This is post-hoc what-if only**, not a pre-registered money strategy or a verified executable bet.

- **SINGLE (highest model-estimated EV = Teixeira, American +165):** R2,000 stake; R0 if loss, R5,300 if win. Winner information is disputed across source reports and no official UFCStats fight-details audit is completed here, so the result stays unresolved.
- **BASKET (four selected sides, R500 each):** Navajo Stirling -179, Ikram Aliskerov -290, Santiago Luna +224, Tallison Teixeira +165. The first three are reported wins with gross returns about R779.33, R672.41, and R1,620.00. The fourth is **DISPUTED**. If it loses, hypothetical bankroll **R3,071.74**. If it wins, **R4,396.74**. Neither outcome is verified profit. All-in exposure R2,000; unused R0.

Selection probabilities and what-if thresholds are retrospective. Three observed winning scenarios and one disputed outcome cannot establish a profitable prospective strategy. UFCash and the listed market favourites each had 5/6 correct *reported* fight winners on the prior undoubted matchup subset, so there is no observed simple pick-accuracy edge on that small set.

## Compound wealth and insolvency

At a fair 2.00 decimal price and independent 50% chance of success on each all-in single, after `n` wins wealth = R2,000 x 2^n, and the probability of surviving all `n` rounds = (0.5)^n. At ten wins, the possible wealth is **R2,048,000** but the survival probability is **0.09765625%**. One loss at any step is R0. This is a mathematical toy, **not a UFCash forecast**; at real sportsbook prices the vig and model error usually make odds even less attractive.

## Open-source expansion research (21 Nov 2026)

| Area | Verified resource | Access/conditions | Current integration |
|---|---|---|---|
| Formula 1 calendar/results | [Jolpica F1](https://github.com/jolpica/jolpica-f1) and [JSON endpoint](https://api.jolpi.ca/ergast/f1/2026.json) | Open source Apache-2.0; public endpoint, rate limits/terms; no bookmaker odds | **Read-only schedule adapter implemented** (`scripts/f1_public_feed.py`). It outputs upcoming races and marks odds/predictions missing; NO F1 wagers are fabricated. |
| Formula 1 historical telemetry | [OpenF1](https://openf1.org/docs/) | Public historical data free from 2023; live access paid | Research-only shortlist; no approved forward model or market price yet |
| Basketball / NBA data | [swar/nba_api](https://github.com/swar/nba_api) | MIT Python client; NBA.com data subject to provider's separate terms | Not installed; must establish predictive validity, data rights and prices before virtual selections |
| Football match history / prices | [Football-Data](https://www.football-data.co.uk/data.php) | Free for individuals, explicitly states *not for commercial/AI bot use*. Confirm permissions before any automated ingestion | **Not scraped or AI-ingested** due explicit restriction |
| Current US NBA/MLB markets | [TheOddsAPI current pricing](https://theoddsapi.com/pricing) | Free 25 calls/day, NBA/MLB h2h US sportsbooks; **not** historical odds or prices executable to a South African user | No keys connected; not installed; don't infer profit or local access |

Do **not** use cracked or illegally distributed betting apps, stolen data, or payment bypasses. Open-source code licenses and API/data access terms are distinct. Additional sports only become eligible for an actual pre-event paper decision once genuine model probabilities and source-attributed, timestamped quotes are available, with no look-ahead leakage.

## Local commands

```bash
python -m unittest discover -s tests -p 'test_*all_in_challenge.py' -v
python -m unittest discover -s tests -p 'test_f1_public_feed.py' -v
python -m scripts.all_in_challenge historical --input research/2026-11-21-qatar-reference-input.json --output /tmp/qatar-basket.json --bankroll 2000 --strategy BASKET
python -m scripts.all_in_challenge historical --input research/2026-11-21-qatar-reference-input.json --output /tmp/qatar-single.json --bankroll 2000 --strategy SINGLE
# Once real future authenticated input exists, freeze ahead of the real event:
python -m scripts.all_in_challenge freeze --input /path/to/real-pre-event-input.json --output results/virtual/unique-round.json
# Paper result reconciliation should be a distinct file, never overwrite a frozen original:
python -m scripts.all_in_challenge settle --input /path/to/original-receipt-and-audited-outcomes.json --output results/virtual/unique-settlement.json
# Read-only F1 race schedule, no odds or bets:
python -m scripts.f1_public_feed --year 2026 --output results/virtual/f1-observation.json
```

`freeze` and `settle` create new files exclusively (`open('x')`). Running a toy historical input with a pre-event freeze is forbidden; it is only accepted by the explicitly retrospective `historical` action.

Original earlier UFCash small-stake policy remains in its own separate scripts; this is a **distinct all-in R0 experiment**, not a change to real betting or financial accounts.
