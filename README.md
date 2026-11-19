# J$A // UFCash Public Worker

A dedicated **R0-infrastructure**, open-source-only UFC research, quality-control, and reproducible model-evaluation repository, independent of J$A's private bankroll ledger and other ventures.

## Current working provenance

- Original trained model: [SolvAI/ufcash](https://github.com/SolvAI/ufcash) at commit `c6b1e8233b172fde6e2dabb8757d351c1a4a5ede` (upstream MIT terms).
- Earlier verified research run: [GitHub Actions 44607768706](https://github.com/jakalsalfa319/AI-auto-generate-video/actions/runs/44607768706), seven matchups, 2026-11-21.
- Original public-reference odds: https://jsa-ai-trading-hq.vercel.app/api/ufc-reference-odds.
- Public J$A model dashboard: https://jsa-ai-trading-hq.vercel.app/ufcash.html.
- **Price limitation:** UFC.com public-display reference odds, neither verified bookmaker opening odds nor executable bet quotes.
- **No betting execution**, no bookmaker credentials, no payment/credits/subscriptions, and no personal financial records in this repository.

## Research architecture

1. **UFCash** runs as the trained upstream model in an isolated GitHub Actions public runner using a pinned upstream commit.
2. **Independent challengers**, including a chronological Elo model and original pre-fight statistical models, must first pass a shared leakage-free evaluation protocol before deployment.
3. **Historical validation:** sealed chronological holdouts, no post-fight information, deduplicated matchups, pre-fight fighter-name resolution, calibration and source provenance.
4. **Event checks:** public UFC pages and [ufc-cal](https://github.com/clarencechaan/ufc-cal) may offer independent schedule references, but a mention is not a confirmed completed bout.
5. **Financial validation:** calculate profit only against correctly timestamped, independently verifiable executable odds, with costs, missing markets and sample exclusions disclosed.

The 12 user-supplied candidate repositories were individually reviewed for license, role, freshness and data-leakage risk in [sources/audit.json](sources/audit.json). Listing a repository is not a license to copy its code or redistribute its datasets.

## The 99.9% ambition

**99.9% is an aspiration, not an achieved or promised fight-winner accuracy.** The system must disclose: accuracy, lower 95% Wilson confidence bound, abstention/coverage, Brier, log loss, expected calibration error, sample size, drawdowns and net ROI if independently verified executable prices exist. A threshold tuned on the same test set is invalid. Claiming 99.9% only becomes defensible after independent, locked, prospective evaluation on enough fights to support the precision claim.

For selective predictions, coverage must be reported alongside precision. Abstaining from difficult matchups is not equivalent to predicting them correctly. Models may improve research usefulness without guaranteeing profit.

## Operation

The workflow `.github/workflows/jsa-ufcash.yml` is intended for **standard public GitHub-hosted runners**, with read-only repository permission, no secrets and an ephemeral environment. The event-specific input is deliberately verified against the 2026-11-21 Qatar card. Do not generalize that historical snapshot into arbitrary future cards. A future general-purpose card input interface must include public fixture validation and event-date safeguards.

The worker downloads public MMA datasets and their source content may evolve; checksums are recorded in the run provenance. UFCash uses Python `joblib` for its serialized model; loading it is potentially code-executing, so keep it on ephemeral isolated runners without credentials. No private data, credentials or account tokens should be passed.

## Licensing

This repository stores independently authored workflow wrapper/documentation and public research *metadata*. No source code from unlicensed/GPL projects is copied into a different-licensed module. Each upstream repo's code and datasets retain their respective rights; review site terms before production redistribution or commercial use.
