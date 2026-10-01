# Spec 07 — README and headline findings

## Goal
A README that gives a stranger the answer in 30 seconds, then shows how to reproduce it. Plus 3–5 headline findings with exact numbers for the LinkedIn post.

## Compute findings (from processed data only; no invented numbers)
Write `src/evgap/findings.py` that prints and saves `data/processed/findings.json` with:
1. Bay Area total EVs, public ports, EVs per public port.
2. The #1 gap ZIP: ZIP, area name/county, EVs, public ports, EVs per port, and how many times the Bay Area average that is.
3. Worst and best county by EVs per public port, and the ratio between them.
4. Number of rankable ZIPs (≥ 200 EVs) with **zero** public ports, and how many EVs live in them.
5. The fastest-growing under-served ZIP (top quartile of 2-year EV growth AND top quartile of gap_score).
6. DC fast reality check: Bay Area BEVs per public DC fast port, and the share of DC fast ports that are Tesla.

## README structure
1. **Title + one-line question**
2. **Headline findings** — 3–5 bullets with numbers from `findings.json`
3. **Map image** (`charts/03_gap_map.png`) + link to the live app if deployed
4. **What this measures** — metric definitions in a short table
5. **Data sources** — DMV (data.ca.gov, file date), NREL AFDC (fetch date), Census ZCTA 2020; links
6. **Limitations** (copy as-is):
   - DMV registrations are a 1 Jan 2026 snapshot by owner ZIP, not where cars charge; commuters charge near work.
   - NREL lists public ports; it doesn't show pricing, reliability, downtime or utilization.
   - ZIP codes and Census ZCTAs don't match perfectly.
   - Tesla Superchargers count as DC fast ports; many are Tesla-first, so non-Tesla drivers may see a bigger gap.
   - Home and workplace charging isn't counted. Areas with many single-family homes need fewer public chargers.
7. **Run it yourself** — 5 commands (venv, install, `.env`, fetch, build, app)
8. **Project structure** — short tree
9. **Why I built this** — 2–3 sentences in first person (placeholder text the user will edit; mark it `<!-- EDIT ME -->`)
10. **License** — MIT

## GitHub metadata (used in Prompt 8)
- Description: `Which Bay Area ZIP codes have the most EVs per public charger? Public DMV + NREL data, Python, Streamlit.`
- Topics: `electric-vehicles, ev-charging, bay-area, data-analysis, geospatial, streamlit, python, open-data`

## Done when
- README renders well on GitHub (images show, links work)
- Findings printed to terminal with exact numbers
- Commit `step 07: README and findings`
