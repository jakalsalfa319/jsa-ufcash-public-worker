# J$A Frozen Frontier: future UFC research-card workflow

**Status:** implemented for future events after 21 November 2026. Reuse the permanent [approved fitted model release](https://github.com/jakalsalfa319/jsa-ufcash-public-worker/releases/tag/jsa-frontier-v2-fitted-2026-11-20) without retraining. Both 21 November journals are unchanged.

This workflow deliberately produces **no future forecasts** until an actual future UFC event and a complete, source-attributed pre-fight feature snapshot are supplied.

## What is implemented

- [prepare_future_card.py](../scripts/prepare_future_card.py) converts an existing UFCash pre-fight parquet table into an **UNREVIEWED** JSON draft. Missing values remain null rather than invented zeros.
- [future_card_inference.py](../scripts/future_card_inference.py) requires a reviewed card, event starting in the future, capture/review timestamps, exact 50 original features, 6 derived interactions, and a fresh UFC.com same-bout HTML check. Invalid or incomplete fights are blocked.
- [Free GitHub Actions workflow](../.github/workflows/frozen-future-inference.yml) runs lightweight tests on code changes. A manual dispatch using a reviewed future card downloads the **actual** fitted checkpoint, verifies its hardcoded SHA-256 and runs inference with pinned Python packages.
- Output is an expiring **30-day research artifact** with model/source/input fingerprints, original matchup names, and no completed outcomes or betting transactions. It never overwrites the earlier journals or Finance.

## Prepare a real next event

1. Verify a genuine future event's card and start time on UFC.com. Make sure the UFCash pre-event features are derived only from prior events and source data available **before** the contest. A public historical dataset can be revised later, so independent point-in-time evidence matters.
2. Create the source feature parquet using the existing upstream UFCash build for the confirmed card. All target fights must have outcome UPCOMING and no known winner.
3. In a checkout with pandas and pyarrow installed, run the following command. **Every date/path/URL here is a placeholder, NOT a real event:**

    python -m scripts.prepare_future_card --features /path/to/features.parquet --event YYYY-MM-DD --starts-at-utc "YYYY-MM-DDTHH:MM:SSZ" --official-url "https://www.ufc.com/event/REAL-EVENT-SLUG" --output cards/drafts/YYYY-MM-DD.json

4. Open the draft. Review every fighter pair, card changes, UTC start time, date/source of features and all missingOrInvalidFeatures. Recover missing values only from authentic pre-fight records; never invent data or turn unknowns into zero.
5. Only after checking, set reviewStatus to REVIEWED and reviewedAtUTC to the **actual UTC review timestamp**. Commit the card at cards/reviewed/YYYY-MM-DD.json. This review flag is **not** proof that UFCash inputs were independently point-in-time audited.
6. Open [GitHub Actions](https://github.com/jakalsalfa319/jsa-ufcash-public-worker/actions/workflows/frozen-future-inference.yml). Choose Run workflow, and supply the exact committed path cards/reviewed/YYYY-MM-DD.json. The job has read-only repository access and does not place bets.
7. Examine the saved research artifact, including the source SHA-256 and each probability, and keep an independent copy if needed after 30 days. After fights end, use independently verified UFCStats results to measure prospective accuracy, coverage and calibration without modifying the frozen forecast.

## Security and data contracts

The approved checkpoint SHA-256 is:

727b4a535927157257de84f6a7cc3fd5988aba9cabb98ba6bf84e726dc1a3a97

The release contains serialized joblib/pickle model objects. Those can run code when deserialized. The workflow verifies this trusted SHA before loading the release and uses precisely pinned dependency versions.

The output explicitly states featureContentsIndependentlyAudited=false. A current official UFC listing establishes **only** that the exact bout is listed at the time checked. It does not independently verify the engineered feature values, prove that a bout was completed, imply bookmaker odds are executable, or establish a positive wagering return.

## Zero-cost policy

No paid API, extra Vercel serverless function, private ledger access, brokerage credential, automatic wager or subscription is involved. A historical 66.17% result from already-inspected 2026 data is not a guarantee for the next event, and 99.9% accuracy is not established.
