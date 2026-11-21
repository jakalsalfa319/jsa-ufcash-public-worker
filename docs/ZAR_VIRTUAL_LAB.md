# UFCash | Virtual Rand Lab (v1)

**Mode:** no-money retrospective demonstration, not a real or previously placed paper bet.

## Baseline demonstration, 21 November 2026

This is a post-event reconstruction using the **pre-event prediction journal** created on 19 November 2026 and *third-party-reported* BetOnline prices described by The Garcia Report (19 November, claimed sportsbook observation around 09:37 PT). The report is not an independently authenticated bookmaker fill receipt. A 3% model-estimated expected-value screen was **chosen after the event**, so any success is vulnerable to hindsight and must NOT be added to prospective performance.

Using R1,000 pretend bankroll, four scenarios with R10 stakes were selected: Navajo Stirling -179, Ikram Aliskerov -290, Santiago Luna +224, and Tallison Teixeira +165. Three have independently reported outcomes aligning with the selections: R5.59, R3.45, R22.40 net. The fourth has contradictory published winner reports (secondary reporting Teixeira, regional official UFC-hosted scorecard Gaziev); this discrepancy is preserved as **DISPUTED**. Therefore **R31.44** is the sum of three scenario wins; the final hypothetical account balance ranges from **R1,021.44** (Teixeira scenario loses) to **R1,047.94** (Teixeira scenario wins). Do not call either endpoint verified profit.

Winner-pick accuracy in the same six undoubted, reported bouts is **5/6 (83.33%)** for the frozen original UFCash predictions and **5/6 (83.33%)** for the 19-Nov price-market favourites. The model did **not** demonstrate an advantage over a naïve favourite-picking baseline on these six bouts.

## Verified source references

- Frozen research snapshot: https://github.com/jakalsalfa319/jsa-ufcash-public-worker/blob/main/public/prospective/2026-11-21.json
- Reference quote article (19 November): https://www.thegarciareport.com/posts/ufc-qatar-prochazka-stirling-betonline-moneylines/
- Results reporting: https://www.mmafighting.com/ufc/522605/ufc-qatar-results-prochazka-vs-stirling
- Contradictory Gaziev scorecard: https://us.ufcespanol.com/news/ufc-qatar-official-scorecards-prochazka-vs-stirling

## Accounting and safeguard rules

- All bankrolls and payouts are **ZAR fictional** and no transaction, deposit, withdrawal, wallet, or bookmaker call is performed.
- Stake = 1% of chosen starting pretend bankroll (maximum 1%) and total risk per card cannot exceed 5%. Each selection is at fixed stake, independent of previous event results.
- Selection = whichever side has the higher `model P(selection) × reference decimal odds - 1` provided that the max is at least 3% *under the model's assumed calibration*.
- American -179 becomes 1 + 100/179 decimal; +224 becomes 1 + 224/100. Net win = stake × (decimal - 1), rounded to rand cents; loss = -stake.
- Draw, no contest, cancellation, replacement: exclude and treat as hypothetical void only after rule/outcome verification. Disputed cases remain unresolved.
- No single event, handpicked threshold, or observed winners justify a profitability claim; use a predetermined rule across many future independently timestamped cards.

## Next genuine test

**Next UFC event:** 5 December 2026, *Adesanya vs Magomedov* in Riyadh (official UFC listing: https://www.ufc.com/event/ufc-fight-night-december-05-2026). UFCash has no publicly verified, SHA-locked December 5 pre-event output in this repository as of 21 November. Therefore **zero** genuine future paper orders have been made for that event. Do not invent probabilities or stakes. Capture full card, build genuine point-in-time features, generate frozen model outputs from approved fitted artifact, capture independently timestamped quotes, then freeze simulated decisions **before the event**. After the event, audit official outcomes and compare performance against same-date market favourites, R1,000 no-bet baseline, net ROI and drawdown.