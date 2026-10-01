# Spec 03 — Build ZIP-level metrics

## Goal
`python -m evgap.build` turns raw data into `data/processed/zip_metrics.parquet` and `zip_metrics.csv` (one row per Bay Area ZIP) plus `county_metrics.csv`, and prints sanity summaries.

## Step by step

### 1. Bay Area ZIP list
- Load `zcta_county_rel.txt`. Keep rows whose county GEOID is in `BAY_AREA_COUNTIES`.
- A ZCTA can straddle counties: assign each ZCTA to the county with the **largest land-area overlap** (use the land-area-of-intersection column).
- Output: `zip` (5-char string), `county`.

### 2. EVs per ZIP (DMV)
- Normalise DMV column names to snake_case: expect something like `date, zip_code, model_year, fuel, make, duty, vehicles`. Print a mapping if names differ.
- Keep: `duty` == Light (case-insensitive), `fuel` in {`Battery Electric`, `Plug-in Hybrid`}, ZIPs that are 5 digits.
- Aggregate per ZIP: `bevs`, `phevs`, `evs = bevs + phevs`. Do this for both files → `evs_2026`, `evs_2024`.
- Also keep total light-duty vehicles per ZIP (all fuels) → `all_vehicles`, so we can compute `ev_share = evs / all_vehicles`.

### 3. Public chargers per ZIP (NREL)
- Load `afdc_ca_elec.json` → `fuel_stations[]`.
- Per station: `zip` (first 5 chars), `ev_level2_evse_num`, `ev_dc_fast_num`, `ev_level1_evse_num`, `ev_network`, `latitude`, `longitude`, `facility_type`. Treat nulls as 0.
- If `zip` is missing or invalid, point-in-polygon the station's lat/lon against ZCTA shapes to get one. Print how many needed this and how many stayed unmatched.
- Aggregate per ZIP: `stations`, `l2_ports`, `dcfc_ports`, `l1_ports`, `tesla_dcfc_ports` (where `ev_network` contains "Tesla"), `top_network` (network with most ports).
- Save station-level Bay Area rows to `data/processed/stations_bay_area.parquet` (the app uses them for dots on the map).

### 4. Join and compute
For each Bay Area ZIP (left join from the ZIP list; missing counts = 0):

| Column | Formula |
|---|---|
| `public_ports` | `l2_ports + dcfc_ports` (exclude L1) |
| `evs_per_port` | `evs_2026 / public_ports`; if `public_ports == 0` → `NaN` and `no_public_ports = True` |
| `bevs_per_dcfc` | `bevs_2026 / dcfc_ports`; `NaN` if 0 |
| `ev_growth_2y` | `evs_2026 / evs_2024 - 1`; `NaN` if baseline 0 |
| `ev_share` | `evs_2026 / all_vehicles_2026` |
| `rankable` | `evs_2026 >= MIN_EVS_FOR_RANKING` |
| `gap_score` | among rankable ZIPs: percentile rank (0–100) of `evs_per_port`; ZIPs with 0 ports and rankable = 100 |
| `gap_rank` | 1 = biggest gap, among rankable ZIPs |

### 5. County summary
Per county: total EVs, BEVs, public L2, DCFC, `evs_per_port`, `ev_growth_2y`. Plus a "Bay Area total" row. Save `county_metrics.csv`.

### 6. Outputs
- `data/processed/zip_metrics.parquet` and `.csv` (commit the CSV)
- `data/processed/county_metrics.csv` (commit)
- `data/processed/stations_bay_area.parquet` (gitignored)
- `data/processed/build_meta.json`: DMV labels used, NREL fetch time, row counts, unmatched station count

## Printed summary
- Bay Area totals: EVs (BEV/PHEV), public L2 ports, DCFC ports, EVs per public port
- County table
- Top 15 ZIPs by `gap_score` with county, EVs, ports, EVs per port
- Count of rankable ZIPs with zero public ports

## Done when
- 150–300 Bay Area ZIPs in output
- No negative values; no infinities (zero-port cases are `NaN` + flag)
- Station unmatched rate < 1%
- Sum of county EVs == sum of ZIP EVs
- Commit `step 03: build ZIP metrics`
