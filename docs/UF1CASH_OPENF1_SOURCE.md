# UF1Cash independent OpenF1 source freshness

Historical F1 model results from Jolpica were incomplete/stale in the 22 Nov 2026 check (15 races; latest 24 May). Added a second, independent, free historical source OpenF1: https://openf1.org/docs/ . OpenF1 historical sessions are free without API keys, intended for personal, educational, non-commercial research. Live session access is paid; do not use it.

`scripts/uf1cash_openf1_freshness.py` queries only `GET /v1/sessions?year=2026&session_type=Race` and then the latest completed race's `/v1/session_result?session_key=...` after a 30-minute post-session delay. It requires a reasonably complete finishing classification and rejects duplicate positions/drivers. It outputs source date, age and reliability flags, with NO betting odds, future model forecast or virtual paper picks.

Outputs are run-specific GitHub Actions artifacts in `results/virtual/f1-openf1-freshness.json`, not an assertion that Jolpica and OpenF1 must always agree. If sources disagree, keep stale/incomplete status until reconciled with official race results. Do not use this as a stand-alone betting model.

R25,000 virtual challenge, R3,071.74 currently available, disputed historical R500 and 100% all-in qualifying round rule remain unchanged.
