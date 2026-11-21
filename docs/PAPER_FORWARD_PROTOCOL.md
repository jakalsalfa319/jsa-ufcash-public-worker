# UFCash | Prospective R0 paper-trial protocol

**Status:** Research-only software implementation. No live bets, account access, funding transfers, bookmaker API, or profitability certification.

## What exists

`python -m scripts.paper_forward freeze --input <genuine-pre-event-input>.json --output results/paper/<event-id>-frozen.json`

`python -m scripts.paper_forward reconcile --snapshot results/paper/<event-id>-frozen.json --outcomes <verified-results-review>.json --output results/paper/<event-id>-reconciliation.json`

Both commands **refuse to overwrite existing files**. All timestamps must include UTC offsets. `freeze` uses the *runner's real current UTC time* and blocks freezing when the event has started. Integrity SHA-256 discourages accidental edits but is not independent proof that a supplied prediction or quote originated when claimed.

### Input shape

```json
{
  "schema":"JSA_UFCASH_FORWARD_INPUT_V1",
  "eventId":"REAL-FUTURE-EVENT-ID",
  "eventStartUTC":"YYYY-MM-DDTHH:MM:SSZ",
  "predictionsCapturedAtUTC":"YYYY-MM-DDTHH:MM:SSZ",
  "predictionSourceUrl":"https://github.com/.../immutable-predictions.json",
  "predictionSourceSha256":"64-lowercase-hex-sha256-of-prior-forecast",
  "modelId":"SHA-locked model/release ID",
  "policy":{"demoBankroll":1000,"stakeFraction":0.01,"maxTotalExposureFraction":0.05,
            "minExpectedRoi":0.03,"maxQuoteAgeMinutes":120},
  "fights":[{"red":"Fighter A","blue":"Fighter B","modelPRed":0.60,
             "quote":{"sourceName":"Named public market source",
                      "sourceUrl":"https://actual-source/actual-market-snapshot",
                      "capturedAtUTC":"YYYY-MM-DDTHH:MM:SSZ",
                      "redAmerican":-120,"blueAmerican":+110}}]
}
```

**The example above is a schema, not a real card or quote.** For fights without reliable data use `"modelPRed":null` and/or `"quote":null`. Do not fill missing fields with fabricated numbers. The source time is user-supplied metadata and must be independently inspected for genuine prospective evidence; this program cannot verify a bookmaker offered the market to a real user at that time.

## Decision and settlement protocol

1. Before the *event starts*, independently review the actual fight card, exact two fighter identities, the trained model artifact hash and source-feature cutoff. The input predictions and model weights must exist before the fight, with no post-fight features.
2. Capture a real-source quote with the precise observation time. Price must be attributable, chronologically possible, and at most 120 minutes old at freeze time. A reference/public displayed quote is **not** an executable bet receipt. Missing/stale/unattributed quotes produce no paper decision.
3. The versioned threshold (3% hypothetical EV), fixed demo stake cap (1% opening virtual bankroll) and card exposure cap (5%) are exploratory and must not be optimized against the event being settled. Highest hypothetical EV is considered first, with stable tiebreak ordering.
4. Freeze before the event using a private or public repository commit and separately preserve the resulting SHA. Track quote evidence and model source independently. Merely setting earlier timestamps in JSON does **not** prove the decision was pre-event. A trustworthy commit/run timestamp is required for prospective classification.
5. After actual bout outcomes become available, record them in a **new** outcomes file. A draw, no contest, postponement, cancellation, changed opponent, disputed score, or pending result does not count as a win or loss. Don't invent missing winners.
6. Reconcile into a **new** report. The script requires UFC/UFCStats-hosted links for decisive results but does **not** check the webpage's contents by itself. Therefore every reported winner and every scenario cashflow remains *unverified* until an independent content audit passes. A source URL alone does not equal verified evidence.
7. Inspect independently sourced final UFCStats fighter statuses. Score Brier and winner accuracy with clear denominators; separately inspect quote coverage, abstentions, uncertainty, timestamp issues, and drawdown. Never label scenario P/L as an actual, bookmaker-validated payout.

## Required next-step integration

- Connect a real *future* UFC event card to the already fitted, SHA-pinned Frontier v2 model. Do not retrain on the evaluation event.
- Add a separate, independently sourced and timestamp-audited real bookmaker quote capture with appropriate legal/data-rights review; no paid service or broker authorization is needed for R0.
- Add independent official source-content cross-checks and event-complete/eligibility review before considering a verified settlement.
- Only after enough genuinely prospective events, evaluate calibration, per-bet confidence intervals and decision stability. Retrospective 2026 accuracy of 66.17% does not imply betting profit.

## Caveats

- A SHA checks file integrity, not independent chronology or authenticity.
- Quotes are **manual/public references, not executable prices**; `verifiedExecutableOdds` remains false and `validatedPaperRoi` remains null.
- A `PAPER_DECISION_RECORDED` is a research selection, not a simulated fill authenticated by a bookmaker.
- Any dispute about a winner must use `DISPUTED` until the official detail page is checked.
- `tests/test_paper_forward.py` uses **invented test fighters** and a **fictional event**, exclusively to exercise the engine. Do not count these scenarios as actual UFC predictions, event accuracy or paper returns.