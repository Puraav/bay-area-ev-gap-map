# Spec 05 — Static charts for LinkedIn and README

## Goal
`python -m evgap.charts` exports 3 PNGs into `charts/`, readable on a phone feed (LinkedIn shows images ~1200 px wide).

## General style
- 1200 × 1200 px (square) at dpi 150; white background; one sans-serif font.
- Title = the finding with its number (e.g. "Palo Alto ZIP 94301 has 412 EVs per public charger"), not a topic.
- Subtitle line: "Data: CA DMV (Jan 2026), NREL AFDC (Oct 2026). Public ports only."
- Grey bars by default; one accent colour for the bar(s) the title is about.
- Values printed on bars; no gridline clutter; no 3D, no legends unless necessary.
- Small footer: `github.com/Puraav/bay-area-ev-gap-map`.

## Charts
1. **`01_top_gap_zips.png`** — horizontal bar chart: top 15 rankable ZIPs by EVs per public port, labelled "ZIP · City/County". Accent the #1 bar.
2. **`02_county_comparison.png`** — horizontal bars: EVs per public port by county, sorted; dashed line for the Bay Area average. Accent the worst county.
3. **`03_gap_map.png`** — static choropleth of `gap_score` for the 9 counties (geopandas plot), county borders drawn thin, the top 5 gap ZIPs labelled.

Optional 4th: **`04_growth_vs_ports.png`** — scatter: x = 2-year EV growth, y = EVs per port, dot size = EVs; label the 5 most extreme ZIPs. Title states what the top-right quadrant means ("fast-growing and under-served").

## Done when
- 3 (or 4) PNGs exist in `charts/`, each under 1 MB
- Every title contains a real number from the data
- Commit `step 05: charts` (commit the PNGs)
