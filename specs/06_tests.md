# Spec 06 — Tests and quality checks

## Goal
Fast tests (`pytest -q` in < 10 s) that run on the committed processed CSVs, so they pass without re-downloading data.

## Tests to write (`tests/test_build.py`)
1. `zip_metrics.csv` loads; `zip` column is 5-char strings; no duplicate ZIPs.
2. Every `county` is one of the 9 Bay Area counties.
3. 150 ≤ row count ≤ 300.
4. Counts (`evs_2026`, `bevs_2026`, `l2_ports`, `dcfc_ports`) are ≥ 0 integers.
5. `public_ports == l2_ports + dcfc_ports` for every row.
6. `evs_per_port` is NaN exactly where `public_ports == 0`; otherwise equals `evs_2026 / public_ports` (tolerance 1e-6).
7. Every rankable ZIP has `evs_2026 >= 200`; `gap_score` is within [0, 100] for rankable ZIPs and NaN otherwise.
8. `gap_rank` is 1..N with no gaps among rankable ZIPs.
9. County totals in `county_metrics.csv` equal the sum of their ZIPs.
10. A unit test for the ZCTA→county "largest land overlap" function using a tiny hand-made DataFrame.
11. A unit test for the DMV filter (light duty + BEV/PHEV only) on a tiny hand-made DataFrame.

## Also
- `ruff check .` and `ruff format --check .` pass.
- Add a GitHub Actions workflow `.github/workflows/ci.yml` that installs the package and runs ruff + pytest on push.

## Done when
- `pytest -q` all green, ruff clean
- Commit `step 06: tests and CI`
