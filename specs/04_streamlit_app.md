# Spec 04 — Streamlit app

## Goal
`streamlit run app/streamlit_app.py` opens a clean, fast app that lets anyone find the charging gaps in the Bay Area.

## Data loading
- Read `data/processed/zip_metrics.csv` and `county_metrics.csv` (committed, so the app works without fetching).
- Read ZCTA geometries for Bay Area ZIPs. Precompute a simplified GeoJSON once in build step if missing: `data/processed/bay_area_zcta.geojson` (simplify to ~0.0005 degrees tolerance; commit it if < 5 MB).
- Stations parquet is optional: if present, show station dots; if not, hide that layer.
- Cache loaders with `@st.cache_data`.

## Layout

**Header:** title "Where the Bay Area is short on EV chargers", one-line subtitle with data dates (from `build_meta.json`), and 4 metric tiles: total EVs, public L2 ports, DC fast ports, EVs per public port.

**Sidebar filters:**
- County multiselect (default: all 9)
- Metric to map: `gap_score` (default), `evs_per_port`, `bevs_per_dcfc`, `ev_growth_2y`, `ev_share`
- Toggle: "Show charging stations" (dots)
- Toggle: "Only ZIPs with ≥ 200 EVs"

**Tab 1 — Map**
- pydeck `GeoJsonLayer` choropleth of the selected metric; sequential single-hue color scale (light → dark = bigger gap). ZIPs with 0 ports outlined in a contrasting color.
- Tooltip: ZIP, county, EVs, L2 ports, DCFC ports, EVs per port, gap rank.
- Optional `ScatterplotLayer` for stations (small dots; DCFC slightly larger).
- Initial view centered on the Bay Area (~37.6, -122.2), zoom ~8.5.

**Tab 2 — Rankings**
- Sortable table of rankable ZIPs: rank, ZIP, county, EVs, BEVs, L2, DCFC, EVs per port, 2-year EV growth, top network.
- Download CSV button.

**Tab 3 — ZIP detail**
- Selectbox for ZIP → its numbers vs county and Bay Area averages, ports by level, networks breakdown, growth.

**Tab 4 — Counties**
- Bar chart of EVs per public port by county + the county table.

**Tab 5 — Method**
- Data sources with links, definitions of each metric, the limitations list (copy from spec 07).

## Quality bar
- Loads in under ~3 seconds locally after first run.
- No warnings or tracebacks in the terminal.
- Works at laptop width; readable on a phone.
- Numbers formatted with thousands separators; ratios with 1 decimal.

## Done when
- App runs locally with no errors; all 5 tabs render
- Changing the county filter updates map, tiles and table
- Commit `step 04: streamlit app`
