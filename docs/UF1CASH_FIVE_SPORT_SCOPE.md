# UF1Cash five-sport activation, 22 November 2026

UFC 50%, Formula 1 12.5%, rugby union 12.5%, horse racing 12.5% and cricket 12.5% are percentages of **research/development effort**, not compulsory percentages of wagers.

User-authorised five-sport scope replaces the former UFC 75% and F1 25%. The R25,000 virtual goal and rule to commit 100% of available virtual ZAR on every eligible round remain intact. Current working virtual available balance R3,071.74, R500 disputed historic stake locked. No real bookmaker wagers, topups, or deposits.

The UFC and F1 research remain. Rugby and horse racing are activated using existing pre-event validators in scripts/multisport_markets.py. Rugby requires explicit three-way 80-minute win/draw/loss probabilities and prices. Horse racing requires a complete declared field, every runner's fixed WIN price and rejects scratchings. Those adapters are NOT trained models or automated odds collectors.

The new cricket T20/T20I adapter requires an explicitly labelled two-way match-winner market INCLUDING Super Over, complete team probabilities and fixed decimal odds for both teams. This differs from a standard three-way rugby market. Tie/no result, revised overs, abandoned games, DLS, and bookmaker-specific void conditions need review during settlement. Unsupported and unverified conditions must not become wins.

Cricket training data can come from Cricsheet, which now explicitly licenses match data under ODC-BY 1.0. Attribution: Cricsheet.org (ODC-BY 1.0). Source: https://cricsheet.org/article/licensing-and-venues-registry/ . The source parser only handles historical results before a fixed training cutoff and never creates an odds quote or prediction.

For all sports, a future simulated selection requires a pre-event forecast, model SHA, genuine source-attributed odds observation and a timestamped independent paper receipt. No guessed prices or results. A completed source adapter is not evidence of actual profitability. Rugby-Data (https://github.com/transientlunatic/Rugby-Data) is a possible source but permission to ingest is not assumed. Jolpica F1 is noncommercial under its API terms. Horse racecard sources must be reviewed for lawful usage.
