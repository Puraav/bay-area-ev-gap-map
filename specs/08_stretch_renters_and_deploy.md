# Spec 08 (optional) — Renters layer + live deployment

## Part A — Who can't charge at home? (Census ACS)
People who rent or live in apartments usually can't install a home charger, so they depend on public charging. Add this to the gap.

### Data
- Census ACS 5-year API, latest available vintage (try 2024, fall back to 2023):
```
https://api.census.gov/data/<YEAR>/acs/acs5
  ?get=NAME,B25003_001E,B25003_003E
  &for=zip%20code%20tabulation%20area:*
```
  - `B25003_001E` = occupied housing units, `B25003_003E` = renter-occupied.
- Optional second pull: `B25024` (units in structure) to compute share of homes in buildings with 5+ units.
- No key needed at this volume; if rate-limited, read `CENSUS_API_KEY` from `.env`.
- Save raw JSON to `data/raw/acs_tenure.json`; add to `fetch.py` behind a flag `--with-acs`.

### Metrics
- `renter_share = B25003_003E / B25003_001E`
- `priority_score` (rankable ZIPs) = mean of `gap_score` and the percentile rank of `renter_share` (0–100).
- Add both to `zip_metrics.csv`, a "Renter share" option in the app's map metric, and a 5th finding: "The top ZIP by priority score (many EVs, few chargers, mostly renters)".

### Done when
- New columns present, tests extended (renter_share in [0,1])
- README findings updated
- Commit `step 08a: renters layer`

## Part B — Deploy to Streamlit Community Cloud (user does the clicks)
Claude Code prepares; the user deploys:
1. Make sure the app runs from committed files only (processed CSVs + simplified GeoJSON); no API key needed at runtime.
2. Add `requirements.txt` (pinned) for Streamlit Cloud if `pyproject.toml` isn't picked up.
3. Push to GitHub.
4. User: go to share.streamlit.io → New app → pick the repo, branch `main`, file `app/streamlit_app.py` → Deploy.
5. Put the public URL in the README and the repo's "Website" field.

### Done when
- Public app URL loads in a fresh browser
- README links to it
- Commit `step 08b: deploy`
