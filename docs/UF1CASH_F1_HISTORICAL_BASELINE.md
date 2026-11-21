# UF1Cash experimental F1 historical baseline

The `scripts/uf1cash_f1_ratings.py` module builds a continuously updated **historical** Elo-style ranking from Jolpica F1 classified race results. It excludes every race on or after its explicit `asof` cutoff. It compares model top-1 winner accuracy with the pole sitter winner frequency, and reports multiclass log loss. These are retrospective historical results, not a validated prospective betting strategy.

The baseline is experimental with fixed K, grid and softmax temperature; the parameters are *not* presented as professionally calibrated, and the open-source API's terms are CC BY-NC-SA 4.0, noncommercial only: https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md

The daily read-only Actions job attempts to download 2024, 2025 and 2026 results via public API endpoints, recomputes chronological ratings and preserves a run artifact. Network/API failures fail this optional step only and do not create false predictions. A genuine prospective race market still requires a pre-event confirmed entry list, qualifying grid, source-checked model calibration, fresh bookmaker odds with permitted use, matching settlement terms and an immutable pre-race timestamped paper receipt.

No actual bet is placed. The R3,071.74 working virtual wallet, disputed R500 and R25,000 milestone are not affected by these historical model metrics.
