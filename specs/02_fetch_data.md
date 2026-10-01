# Spec 02 — Fetch the raw data

## Goal
`python -m evgap.fetch` downloads every raw input into `data/raw/` and prints a summary. Re-running skips files that already exist unless `--force` is passed.

## Sources

### A. CA DMV — Vehicle Fuel Type Count by Zip Code
- Dataset page: https://data.ca.gov/dataset/vehicle-fuel-type-count-by-zip-code
- **Don't hardcode file URLs.** Get them from the CKAN API:
  `https://data.ca.gov/api/3/action/package_show?id=vehicle-fuel-type-count-by-zip-code`
  → `result.resources[]`, each with `name` and `url`.
- Download the two resources whose `name` contains `config.DMV_LATEST_LABEL` ("1/1/2026") and `config.DMV_BASELINE_LABEL` ("1/1/2024"). If the latest label isn't found, pick the most recent date available and print a warning.
- Save as `data/raw/dmv_latest.csv` and `data/raw/dmv_baseline.csv`. Save which resource names were used to `data/raw/dmv_sources.json`.

### B. NREL Alternative Fuel Stations API (EV chargers)
- Docs: https://developer.nrel.gov/docs/transportation/alt-fuel-stations-v1/all/
- One request:
```
GET https://developer.nrel.gov/api/alt-fuel-stations/v1.json
    ?api_key=<NREL_API_KEY from .env>
    &fuel_type=ELEC&state=CA&status=E&access=public&limit=all
```
- Save the full JSON to `data/raw/afdc_ca_elec.json` and the fetch timestamp to `data/raw/afdc_meta.json`.
- On HTTP errors, print the status and response body and exit non-zero.

### C. Census ZCTA ↔ county relationship file (2020)
- Expected URL: `https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt`
- If it 404s, browse `https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/` and use the national ZCTA-to-county file there.
- Save to `data/raw/zcta_county_rel.txt` (pipe-delimited).

### D. Census ZCTA boundaries (cartographic, 2020, 1:500k)
- Expected URL: `https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_zcta520_500k.zip`
- If it 404s, browse `https://www2.census.gov/geo/tiger/GENZ2020/shp/` for the ZCTA file.
- Save the zip to `data/raw/zcta_2020_500k.zip` (don't unzip into git).

## Implementation notes
- Use `requests` with a timeout and streaming for large files; show simple progress (MB downloaded).
- Write a small `download(url, dest, force=False)` helper.
- Accept `--force` via `argparse`.

## Printed summary (example shape)
```
DMV latest:   1/1/2026 file, 2,xxx,xxx rows
DMV baseline: 1/1/2024 file, 2,xxx,xxx rows
NREL:         xx,xxx public CA EV stations (fetched 2026-10-01T..)
ZCTA rel:     xx,xxx rows
ZCTA shapes:  xx MB
```

## Done when
- All 6 files exist in `data/raw/` (+ the two `*_sources/meta.json` files)
- NREL returned **> 10,000** California stations
- Both DMV files load in pandas and contain a fuel column with values including `Battery Electric` and `Plug-in Hybrid`
- Print the DMV column names exactly as they appear (we'll normalise them in step 03)
- Commit `step 02: fetch raw data` (raw data itself stays gitignored)
