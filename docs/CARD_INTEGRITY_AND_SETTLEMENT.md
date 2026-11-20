# J$A research integrity: 21 November 2026 UFC Qatar

**Release:** Card Integrity Gate v1 + Status-Safe Settlement v2  
**Existing Frontier model remains unchanged.** These tools improve source and scoring correctness, not the trained model's reported 2026 winner accuracy.

## Verified 20 November official-card checkpoint

- Official UFC card: https://www.ufc.com/event/ufc-fight-night-november-21-2026
- UFC published update: https://www.ufc.com/news/updates-ufc-qatar
- UFC weigh-in article: https://us.ufcespanol.com/news/official-weigh-results-ufc-qatar-prochazka-vs-stirling
- **Recorded GitHub run:** https://github.com/jakalsalfa319/jsa-ufcash-public-worker/actions/runs/44762273907
- **Source HTML SHA-256:** `b68b1e828401885bd6a2a6e22c7f5ec85b7f2539b9ed21ae72264c49005259cf`
- **UTC source check:** 2026-11-20T15:20:35.500179+00:00
- **Result:** 7/7 of J$A's frozen matchups identified within the SAME individual UFC bout markup.
- No bout was assigned a result, no wager was submitted, and no reference odds were labeled executable.

The independent check explicitly rejects false pairing from two names merely appearing on the same webpage, matches accents in fighter names, and refuses to certify a changed/missing fighter pair. It also checks that the two saved journals were created **before** their event.

The 20 November weigh-in coverage reported one missed weight, Tahir Abdullayev, in a *different* bout from J$A's seven tracked pairs. This does **not** prove that tomorrow's card is unchanged; recheck the source before the event.

A source listing establishes only that the matchup is listed, not that a bout is completed or eligible for accuracy scoring.

## One-time free scheduled recheck

[Card integrity workflow](../.github/workflows/card-integrity.yml) uses public GitHub Actions with a read-only token, pinned GitHub actions and no bookmaker/private ledger credentials. It runs on code changes or manual dispatch and schedules one event-morning check for **21 November at 09:30 UTC** (11:30 South African time). Subsequent years are blocked by the event-year guard.

The audit artifact has a 30-day retention; a permanent verified 20 November snapshot is also published at [public/card-integrity-2026-11-20.json](../public/card-integrity-2026-11-20.json). A future failed check should be treated as **source unavailable/card changed**, never an invented confirmation.

## Result states and how they affect accuracy

| Bout status | Count toward winner accuracy? |
|---|---|
| COMPLETED, decisive verified outcome | Yes, for each model with a valid frozen probability |
| DRAW | No |
| NO_CONTEST | No |
| CANCELLED | No |
| REPLACED | No, original archived opponent is not a new fight |
| POSTPONED | No |
| PENDING / unknown outcome | No |

The settlement tool [scripts/settle_event_v2.py](../scripts/settle_event_v2.py) reconciles both original v1 and Frontier v2 journals. It can calculate UFCash, odds-free ML, Frontier and Frontier's locked confidence-selected scores **on the same decisive completed bouts for which each model supplied a probability**.

### Workflow after actual results exist

1. Copy [the seven-row PENDING template](../templates/ufc-qatar-2026-11-21-outcomes.csv). Do not edit the frozen input journals.
2. Check the completed fight and winner against an **independent official UFC/UFCStats source**, noting the exact HTTPS URL and UTC verification timestamp.
3. Set each row to `COMPLETED`, `DRAW`, `NO_CONTEST`, `CANCELLED`, `REPLACED`, `POSTPONED` or retain `PENDING`. For COMPLETED include exactly one of the originally frozen fighters as winner; otherwise leave winner blank.
4. After the event has begun, run: `python -m scripts.settle_event_v2 --outcomes path/to/checked.csv --output results/2026-11-21-reconciliation.json`.
5. Inspect the generated report, verify that all outcome-source webpages **actually substantiate their entered results** and publish a **new** settlement file; never overwrite either original pre-event journal.

**Important:** Providing a URL is not by itself proof the webpage supports the claimed winner. The v2 reconciliation intentionally sets `sourceContentsIndependentlyChecked=false` and `RECONCILED_UNVERIFIED_EVIDENCE` until a human or additional independently audited source checker confirms the results. It never computes ROI or claims real betting profit.

## Accuracy standard

Only a legitimately frozen prediction from before an actual contest, followed by an independently confirmed completed result, contributes to prospective hit-rate evidence. Publish 95% Wilson intervals, Brier/log loss, sample sizes and abstention coverage. Seven bouts cannot substantiate 99.9% betting accuracy, regardless of how many the model guesses correctly.

**R0 technology** maintained. No paid subscriptions, finance credential access, automatic wagers, payments, secret tokens or modification of earlier production models.
