# J$A Frozen Frontier v2: fitted-model checkpoint and repeatable research inference

**Status:** New model-snapshot workflow. A successful GitHub Release is the durable, approved model checkpoint. The older Frontier v2 176/266 result remains an **archived run-specific historical benchmark**, not a restored copy of these new fitted model objects.

## What was frozen

The original Frontier v2 family used:

| Fitted model | Ensemble weight |
|---|---:|
| Pre-fight history regularized logistic | 40% |
| Histogram gradient boosting | 20% |
| XGBoost | 20% |
| CatBoost | 20% |

The same 2012–2024 historical training rows (pre-fight features only), 2025 H1 calibration, and 2025 H2 model-selection policy are used. Rather than repeatedly training the histogram booster and receiving slightly different probabilities, [`scripts/model_checkpoint.py`](../scripts/model_checkpoint.py) now exports the **actual fitted objects** from a completed run.

The frozen archive contains a manifest and the four fitted model files. The manifest records feature order, six derived interaction columns, calibration slope, 65%-confidence selection gate, required Python dependencies, training code checksums, source-data fingerprints and 24 saved test vectors with model probabilities. The separately generated receipt holds the archive SHA-256, fixture replay count, and the exact 2026 retrospective score **for that particular newly frozen run**.

The nine input-data SHA-256 fingerprints must match the source archive used for the original November 20 research. A changed dataset **refuses** the freeze until explicitly reviewed and reauthorized.

## Free, long-lived storage

The existing [UFCash worker](../.github/workflows/jsa-ufcash.yml) publishes its archive and receipt as temporary GitHub Actions artifacts. A separate, least-privilege, one-time release job verifies the SHA-256 against its receipt and creates the public release tag:

`jsa-frontier-v2-fitted-2026-11-20`

The release job has **write access only to repository contents**, not finance accounts or bookmaker services. It refuses to change an existing release. A GitHub Release is intended to avoid the 30-day expiration of ordinary Actions artifacts. This is a model research artifact, not a live betting product.

## Using the frozen fitted model on a new event

1. Open the [J$A Releases](https://github.com/jakalsalfa319/jsa-ufcash-public-worker/releases) page and download **both** `frozen_frontier_v2_checkpoint.tar.gz` and `frozen_frontier_v2_receipt.json` from the **same versioned release**.
2. Verify the archive SHA-256 using the receipt and the trusted release reference. Do not load unidentified or unverified checkpoint files. Python joblib/pickle data can execute malicious code if untrusted.
3. Use the same pinned ML package versions listed in the manifest (available from the pinned upstream UFCash dependencies) and generate a new pre-fight `features.parquet` through the original source pipeline.
4. Verify the event card and fighter identities independently, ensure its bouts are marked `UPCOMING` and have unknown outcomes. The frozen inference function refuses past/known results.
5. Run:

```bash
python -m scripts.model_checkpoint \
  --archive frozen_frontier_v2_checkpoint.tar.gz \
  --sha256 YOUR_VERIFIED_RECEIPT_SHA256 \
  --features ufcash/data/processed/features.parquet \
  --event YYYY-MM-DD \
  --output results/frozen_event_YYYY-MM-DD.json
```

The command **never retrains models**, computes new predictions using only pre-event feature inputs, applies the original calibrated slope and 65% research-confidence gate, and refuses to overwrite an existing prediction output. The output explicitly marks fight results as unknown and `betPlaced=false`.

## Verification and limitations

The checkpoint exporter performs a **read-back test**: it serializes fitted models, reloads them from a SHA-matched archive and computes all selected model probabilities on the original 2025 validation fixture. A mismatch fails the run.

The checkpoint therefore demonstrates **repeatability of one fitted model within compatible pinned dependencies**, not reproducibility of the historical training algorithm or proof that its future UFC predictions are accurate. The first archival 176/266 and later 175/266 observed historical scores are not silently reconciled.

Prospective evidence must come from officially verified, completed fights that were genuinely predicted before the event. Draws, cancelled bouts, replacements and no-contests do not count as wins or losses. Confidence-gated accuracy always requires a disclosed coverage and denominator. None of these artifacts prove 99.9% accuracy or betting profitability.

## R0 and safety boundaries

Only public MMA research sources and open-source packages are used on standard public GitHub Actions runners. No API subscription, paid hosted inference, account credentials, private bankroll export, wagering integration, automatic financial action or claim of profitable returns has been added. The earlier 21 November frozen predictions and dashboards remain unchanged.
