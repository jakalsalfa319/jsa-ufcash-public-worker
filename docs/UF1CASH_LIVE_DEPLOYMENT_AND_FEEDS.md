# UF1Cash standalone live site and optional odds research feed

## Source and deployment

The independent site is sourced from the existing public repository jakalsalfa319/jsa-ufcash-public-worker. Its Vercel build root is public/ and public/index.html redirects to public/uf1cash.html without JavaScript. The production browser loads the repository-published user-approved virtual ZAR ledger, not an actual betting account. Existing J$A trading HQ site is deliberately untouched.

## Odds provider (no account/key magically created)

Public catalog and pre-event bookmaker metadata can come from The Odds API v4: https://the-odds-api.com/liveapi/guides/v4/ . Its free plan is currently advertised at 500 credits/month across sports, subject to terms and availability: https://the-odds-api.com/ . A registered user must create a provider key and add it to Settings -> Secrets and variables -> Actions as UF1CASH_ODDS_API_KEY. **Never paste or commit API keys to GitHub.**

scripts/uf1cash_odds_discovery.py runs in the daily **read-only** CI research job on main. It discovers provider sport keys dynamically and uses up to 3 charged odds calls per run, UK region, with event/market coverage only; it never publishes raw odds prices or keys. A missing secret yields NOT_CONNECTED_KEY_REQUIRED, rather than invented quotes. Provider availability may not cover F1, horse racing or UFC in every region. No paid subscriptions are authorized.

Until a genuine pre-event model forecast is frozen and a source-attributed odds record and settlement contract are independently reviewed, the engine makes **zero new paper selections**. Quote timestamps alone do not authenticate executable sportsbook fills. Scraping unknown bookmaker websites or publishing third-party bookmaker data without rights is out of scope.

## Model status

The existing UFC Frontier v2 trained model and its archived checkpoints remain intact. Future UFC inference still requires a reviewed feature card and source proof. Rugby, horse and T20 models are validation adapters, not trained predictive engines. F1 has a public, non-commercial Jolpica schedule adapter. No claim of demonstrated profitability.

## Virtual wallet integrity

Current adopted post-event working virtual balance R3,071.74, original disputed R500 withheld; R25,000 target; every qualifying round stakes 100% of available ZAR, with discretion over market and individual weights; no market qualifies means abstain. UFC 50%, F1/rugby/horse/cricket 12.5% each is research allocation, not forced stake split.

Future changes should add source evidence, tests and audit records before updating a working balance. No funds are transferred and no bookmaker bets are placed.
