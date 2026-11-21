# UFCash Cross-Sport Virtual Lab: Rugby Union & Horse Racing

**Status:** implemented *market adapters*, not proven sport forecasting models, live odds feeds, or placed bets. All money is fictional ZAR. No real wagers or account connection. The opening challenge wallet remains R2,000, untouched.

## What is now implemented

`scripts/multisport_markets.py` validates a complete, named and time-stamped source board, chooses the single highest **model-estimated EV** outcome per sporting event, and creates an input compatible with `scripts.all_in_challenge.plan_round`. Rugby and horses can occupy the same future virtual BASKET round if *genuinely verified* prospective data for each is available. The existing `SINGLE` strategy still selects the highest model-estimated EV among the eligible candidate events, and the whole bankroll goes to it. Every active round must deploy every cent or ABSTAIN without creating a bet.

- Rugby Union: **regulation-time 80-minute full-time 1X2** only, with home, draw, away all represented. No two-way head-to-head, overtime, handicap, totals or live markets are implicitly converted into this market. Require complete probabilities summing to one and all three contemporaneous fixed odds.
- Thoroughbred horse racing: **fixed-odds WIN** only, with all declared runners and probabilities summing to one; missing prices, scratched horses and incomplete race declarations block the whole event rather than silently renormalising an outdated model. No speculative tote dividends, each-way, place, exacta or trifecta pricing.
- Both use exact decimal odds, without rounding through American prices. Individual quotes are preserved with real capture timestamps and source URLs; model predictions must be bundled into an independently timestamped/hashed source envelope before calling the existing all-in gate.
- Winner settlement remains provisional unless the actual source page supports the claimed outcome. Rugby draws count as a valid 1X2 result. Horse dead heats, void markets, changed odds, Rule 4 deductions and other provider-specific settlement cannot yet be adjudicated automatically; treat as DISPUTED until the precise contract is audited.

## Minimum input contracts

The adapter functions take one Python `dict` with one of these schemas:

```json
{
  "schema": "UFCASH_RUGBY_UNION_1X2_BOARD_V1",
  "eventId": "source-specific-match-id",
  "eventStartsUTC": "2026-12-05T15:00:00Z",
  "fixtureStatus": "CONFIRMED_PREMATCH",
  "homeTeam": "Actual home team",
  "awayTeam": "Actual away team",
  "market": "REGULATION_80_MIN_1X2",
  "modelProbabilities": {"home": "0.48", "draw": "0.06", "away": "0.46"},
  "quote": {"capturedAtUTC": "2026-12-05T12:00:00Z", "sourceName": "Actual attributable quote source", "sourceUrl": "https://example.org/actual-match", "priceKind": "FIXED_DECIMAL", "pricesDecimal": {"home": "2.10", "draw": "16.00", "away": "2.15"}}
}
```

```json
{
  "schema": "UFCASH_HORSE_FIXED_WIN_BOARD_V1",
  "eventId": "source-specific-race-id",
  "eventStartsUTC": "2026-12-05T15:20:00Z",
  "raceStatus": "CONFIRMED_DECLARATIONS",
  "course": "Actual racecourse",
  "market": "FIXED_WIN",
  "runners": [
    {"runnerId": "horse-1", "horseName": "Runner 1", "status": "DECLARED", "modelWinProbability": "0.55"},
    {"runnerId": "horse-2", "horseName": "Runner 2", "status": "DECLARED", "modelWinProbability": "0.45"}
  ],
  "quote": {"capturedAtUTC": "2026-12-05T12:00:00Z", "sourceName": "Actual attributable fixed price", "sourceUrl": "https://example.org/actual-race", "priceKind": "FIXED_DECIMAL", "pricesDecimalByRunnerId": {"horse-1": "1.90", "horse-2": "2.20"}}
}
```

These are **schema examples, NOT real prices, predictions or fixtures**. Source links in the examples are placeholders. Don't submit to the genuine R2,000 challenge. The adapter does **not** verify that a provider offers the supplied odds or that your model is trained, calibrated, timestamped or has predictive advantage. All-in's pre-event guard continues to enforce stale quotes, event start, EV threshold, frozen model provenance and bankroll accounting.

## Free-source research for a legal R0 build

### Rugby

- [Rugby-Data](https://github.com/transientlunatic/Rugby-Data) includes URC, Currie Cup, Super Rugby, Six Nations and more; code/data licence and upstream rights must be verified before copying or automated reuse. Existence on GitHub does NOT equal an open licence.
- [rugbyAPI](https://rugbyapi.com/pricing) offers a free personal API key with 50 calls/day for yesterday, today and forthcoming fixtures. Full historical data is paid; don't treat the free plan as a complete model training set or assume any quote data.
- [TommyKilbourn/rugby-rankings](https://github.com/TommyKilbourn/rugby-rankings) describes an international rugby Elo approach; reference the methodology rather than copying code without licence approval. Any published accuracy belongs to that project's evaluation, NOT UFCash.

### Horse racing

- [HorseRacingAPI](https://horseracingapi.org/pricing) offers free yesterday results, including South Africa, with 50 lookups/day and no odds; cannot produce a proper fresh paper bet alone.
- [The Racing API](https://api.theracingapi.com/documentation) includes a free racecards endpoint for today/tomorrow (primarily UK/Irish); current runner odds and more complete history are paid.
- [open-horse-data](https://github.com/Sheep-Meadow-Road-Games/open-horse-data) documents pedigree source rights. Many listed datasets are explicitly CC0/CC BY-SA, but provenance differs by contributor; do not automatically bulk-ingest other people's scrapes or restricted data.
- [Open-Meteo](https://open-meteo.com/) provides free noncommercial weather forecasts/history and CC BY 4.0 data; useful *if* a real course/location and a valid pre-race forecast timestamp exist. Do not use weather reanalyses generated after a race as if they were known beforehand.

## What's not yet present

1. Licensed/reliable historical data and rigorously trained, frozen rugby and horse models with out-of-time performance.
2. Current *attributable* actual pre-event bookmaker fixed-odds quotes and legally permissible capture. No third-party credentials or scraped restricted pages were accessed.
3. Contemporaneous independently timestamped pre-event fixtures/racecards (including verified race scratchings); an API-free research code adapter is not a live feed.
4. New pre-event paper orders. **The initial R2,000 virtual wallet is unchanged.** No historical post-event winner can be turned into a dated paper ticket.

## Local tests

```bash
python -m unittest discover -s tests -p 'test_all_in_challenge.py' -v
python -m unittest discover -s tests -p 'test_multisport_markets.py' -v
```
