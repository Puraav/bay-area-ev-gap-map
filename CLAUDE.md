# CLAUDE.md — project rules for Claude Code

## What this project is
A public portfolio project: **Bay Area EV Charging Gap Map**. It answers: *Which Bay Area ZIP codes have the most electric vehicles per public charging port — where are chargers missing?* It is built from public data only and must be reproducible by anyone with a free NREL API key.

## How to work
- Work **only** on the spec file the user points to (`specs/0X_*.md`). Don't build ahead.
- After implementing, run the spec's **"Done when"** checks and show the output.
- Commit at the end of each spec with a message like `step 03: build ZIP metrics`.
- If a spec is ambiguous, pick the simplest option and state it in one line.
- Never invent data or hardcode results. Every number must come from the pipeline.
- Never put API keys in code or commits. Read them from `.env` via `python-dotenv`.

## Tech stack (don't swap without asking)
- Python 3.11+, virtualenv in `.venv`
- pandas, geopandas, shapely, pyarrow, requests, python-dotenv
- Streamlit + pydeck for the app
- matplotlib for static charts
- pytest for tests
- ruff for linting

## Conventions
- Source code in `src/evgap/`, app in `app/`, tests in `tests/`.
- Paths and constants live in `src/evgap/config.py` only.
- Raw downloads go to `data/raw/` (gitignored). Processed outputs go to `data/processed/` (gitignored except `zip_metrics.csv`, which is committed so the app works without re-fetching).
- ZIP codes are always 5-character strings (keep leading zeros).
- Functions small and typed; a docstring on each public function.
- Print short, human-readable summaries from scripts (counts, totals) so results can be checked.

## Definition of the region
Bay Area = these 9 counties (state FIPS 06):
| County | FIPS |
|---|---|
| Alameda | 06001 |
| Contra Costa | 06013 |
| Marin | 06041 |
| Napa | 06055 |
| San Francisco | 06075 |
| San Mateo | 06081 |
| Santa Clara | 06085 |
| Solano | 06095 |
| Sonoma | 06097 |

## Commands (keep these working)
- `python -m evgap.fetch` — download all raw data
- `python -m evgap.build` — build `data/processed/zip_metrics.*`
- `python -m evgap.charts` — export PNGs to `charts/`
- `streamlit run app/streamlit_app.py` — run the app
- `pytest -q` — run tests
