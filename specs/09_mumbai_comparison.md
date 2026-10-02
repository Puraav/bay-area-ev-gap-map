# Spec 09 — San Francisco vs Mumbai (data-access angle)

## Update (as built)
OpenStreetMap lists only 4 charging stations for Greater Mumbai, and has 15% of NREL's ports in SF, so a chargers-per-EV ratio for Mumbai isn't credible. The comparison is reframed around **what public data exists** in each city (geographic resolution, access method, charger registry, population vintage) plus the EV facts Vahan supports (EV share of cars, vehicle mix). Charts: `05_sf_vs_mumbai_data.png` (scorecard) and `06_mumbai_ev_mix.png`. Port-density and DC-fast metrics are kept in `city_comparison.json` but not headlined.

## Original goal
A fair, city-level comparison of public EV charging in **San Francisco** and **Greater Mumbai**: one table, two charts, and 3 findings. Every number comes from public data, with the caveats stated next to it.

India's data is coarser than California's, so the comparison runs at the **city** level, not ZIP/PIN level.

## Geographies
| | San Francisco | Mumbai |
|---|---|---|
| Unit | SF County (FIPS 06075), which is the same area as the city | Greater Mumbai (BMC area), served by RTOs MH-01 Mumbai Central, MH-02 Andheri, MH-03 Wadala, MH-47 Borivali |
| Population | ACS 5-year B01003 for 06075 | Census 2011 (latest official count). Label it as 2011, with no projections |
| Area (km²) | Census land area | BMC boundary polygon (OSM relation) |

## Data

### A. EV counts
- **SF:** reuse `zip_metrics.csv` (SF County rows): BEV + PHEV light-duty, 1 Jan 2026.
- **Mumbai:** [Vahan dashboard](https://vahan.parivahan.gov.in/vahan4dashboard/) → State: Maharashtra → RTO = each of the 4 above → Y-axis: Vehicle Class, X-axis: Fuel → Excel export, calendar years 2015–2026 (cumulative registrations).
  - Vahan has no public API and sits behind bot checks, **so the user downloads these 4 exports by hand** into `data/raw/mumbai/vahan_<rto>.xlsx`. The pipeline only parses them.
  - Keep fuel = `ELECTRIC(BOV)` (plus `PLUG-IN HYBRID EV` if present).
  - Split into **cars** (`MOTOR CAR`, `LMV`-type classes), **2-wheelers** and **3-wheelers / e-rickshaws**.
  - Registrations are cumulative and not net of scrapped vehicles. State this.

### B. Public chargers (same source for both cities)
- **OpenStreetMap via Overpass:** `amenity=charging_station` inside each city boundary. Use `capacity` or `socket:*` tags for port counts when present; otherwise count 1 per station.
- Run the **same OSM query for SF**, then compare it with NREL's SF count. This gives an OSM-vs-NREL coverage ratio for SF, which shows how much OSM undercounts.
- Optional cross-check for Mumbai: the BEE / MSEDCL public charging station list, if a downloadable version exists. Don't scrape map widgets.

## Metrics (per city)
- EV cars, EV 2-wheelers, EV 3-wheelers (Mumbai). SF: EVs (all are cars or light trucks)
- Public charging stations and ports (OSM) for both cities, plus NREL ports for SF
- **EV cars per public port** (headline, like for like), using OSM in both cities
- DC fast share of ports, where `socket:*:output` ≥ 50 kW or the station is tagged as fast
- Ports per 100k people, and ports per km²
- Top charging networks by port count (OSM `operator` / `network`)

## Outputs
- `src/evgap/mumbai.py` → `data/processed/city_comparison.csv` + `city_comparison.json`
- `charts/05_sf_vs_mumbai.png`: paired horizontal bars for 4 metrics (EV cars per port, ports per 100k, ports per km², DC fast share). SF and Mumbai each get one colour, with direct labels
- `charts/06_mumbai_ev_mix.png`: Mumbai EVs by vehicle type, showing that 2- and 3-wheelers dominate
- New app tab: "SF vs Mumbai" (table + the two charts)
- README section + 3 findings, each with its caveat

## Caveats to print next to the numbers
- OSM coverage differs by city. Show the SF OSM-vs-NREL ratio so readers can judge it.
- Mumbai EV counts are cumulative registrations by RTO and include vehicles no longer on the road. RTO areas only roughly match the BMC boundary.
- Mumbai's EVs are mostly 2- and 3-wheelers that often charge at home or swap batteries, so the headline compares **cars only**.
- Mumbai's population figure is from 2011.

## Done when
- `python -m evgap.mumbai` prints the comparison table with sources and dates
- SF numbers match `county_metrics.csv` exactly
- Tests: SF EVs equal the San Francisco row of `county_metrics.csv`; every metric is non-negative
- Commit `step 09: SF vs Mumbai comparison`
