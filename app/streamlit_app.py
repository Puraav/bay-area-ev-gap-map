"""Bay Area EV Charging Gap Map — Streamlit app."""

import json

import pandas as pd
import pydeck as pdk
import streamlit as st

from evgap import config

st.set_page_config(page_title="Bay Area EV Charging Gap Map", page_icon="⚡", layout="wide")

METRICS = {
    "gap_score": "Gap score (0–100, higher = bigger gap)",
    "evs_per_port": "EVs per public port",
    "bevs_per_dcfc": "BEVs per DC fast port",
    "ev_growth_2y": "2-year EV growth",
    "ev_share": "EV share of light-duty vehicles",
    "renter_share": "Renter share of households",
    "priority_score": "Priority score (gap + renters, 0–100)",
}
LIGHT, DARK = (255, 237, 222), (140, 45, 4)  # single-hue orange ramp
NO_DATA = [210, 210, 210, 120]
ZERO_PORT_OUTLINE = [33, 102, 172, 255]


# ---------- loaders ----------
@st.cache_data
def load_zips() -> pd.DataFrame:
    """ZIP-level metrics (committed CSV)."""
    return pd.read_csv(config.PROCESSED_DIR / "zip_metrics.csv", dtype={"zip": str})


@st.cache_data
def load_counties() -> pd.DataFrame:
    """County-level metrics (committed CSV)."""
    return pd.read_csv(config.PROCESSED_DIR / "county_metrics.csv")


@st.cache_data
def load_geojson() -> dict:
    """Simplified Bay Area ZCTA polygons."""
    return json.loads((config.PROCESSED_DIR / "bay_area_zcta.geojson").read_text())


@st.cache_data
def load_meta() -> dict:
    """Build metadata (data dates, counts)."""
    return json.loads((config.PROCESSED_DIR / "build_meta.json").read_text())


@st.cache_data
def load_stations() -> pd.DataFrame | None:
    """Station-level rows, if the (gitignored) parquet exists."""
    path = config.PROCESSED_DIR / "stations_bay_area.parquet"
    return pd.read_parquet(path) if path.exists() else None


# ---------- helpers ----------
def fmt_int(x) -> str:
    """Thousands separator, or an en dash for missing."""
    return "–" if pd.isna(x) else f"{x:,.0f}"


def fmt_ratio(x) -> str:
    """One decimal, or an en dash for missing."""
    return "–" if pd.isna(x) else f"{x:,.1f}"


def fmt_pct(x) -> str:
    """Percent with one decimal."""
    return "–" if pd.isna(x) else f"{x * 100:.1f}%"


FORMATTERS = {
    "gap_score": fmt_ratio,
    "evs_per_port": fmt_ratio,
    "bevs_per_dcfc": fmt_ratio,
    "ev_growth_2y": fmt_pct,
    "ev_share": fmt_pct,
    "renter_share": fmt_pct,
    "priority_score": fmt_ratio,
}


def ramp(values: pd.Series) -> list[list[int]]:
    """Map values to a light→dark colour ramp using 5th–95th percentile bounds."""
    lo, hi = values.quantile(0.05), values.quantile(0.95)
    out = []
    for v in values:
        if pd.isna(v):
            out.append(NO_DATA)
            continue
        t = 0.0 if hi == lo else min(max((v - lo) / (hi - lo), 0.0), 1.0)
        out.append([round(a + (b - a) * t) for a, b in zip(LIGHT, DARK, strict=True)] + [200])
    return out


def build_layer_data(z: pd.DataFrame, geo: dict, metric: str) -> dict:
    """Attach colours and tooltip strings to the GeoJSON features for the shown ZIPs."""
    z = z.copy()
    vals = z[metric]
    if metric == "evs_per_port":  # zero-port ZIPs are the worst case: paint darkest
        vals = vals.fillna(vals.max())
    z["_fill"] = ramp(vals)
    rows = z.set_index("zip")
    feats = []
    for f in geo["features"]:
        zp = f["properties"]["zip"]
        if zp not in rows.index:
            continue
        r = rows.loc[zp]
        props = {
            "zip": zp,
            "county": r["county"],
            "city": r["city"],
            "evs": fmt_int(r["evs_2026"]),
            "l2": fmt_int(r["l2_ports"]),
            "dcfc": fmt_int(r["dcfc_ports"]),
            "epp": "no public ports" if r["no_public_ports"] else fmt_ratio(r["evs_per_port"]),
            "rank": "not ranked (<200 EVs)" if pd.isna(r["gap_rank"]) else f"#{int(r['gap_rank'])}",
            "metric": FORMATTERS[metric](r[metric]),
            "fill": r["_fill"],
            "line": ZERO_PORT_OUTLINE if r["no_public_ports"] else [255, 255, 255, 180],
            "lw": 3 if r["no_public_ports"] else 0.5,
        }
        feats.append({"type": "Feature", "geometry": f["geometry"], "properties": props})
    return {"type": "FeatureCollection", "features": feats}


# ---------- data ----------
zips_all = load_zips()
counties_all = load_counties()
meta = load_meta()
stations = load_stations()

# ---------- sidebar ----------
with st.sidebar:
    st.header("Filters")
    county_names = list(config.BAY_AREA_COUNTIES)
    sel_counties = st.multiselect("Counties", county_names, default=county_names, key="counties")
    metric = st.selectbox("Metric to map", list(METRICS), format_func=METRICS.get, key="metric")
    show_stations = st.toggle(
        "Show charging stations",
        value=False,
        disabled=stations is None,
        help=None
        if stations is not None
        else "Run `python -m evgap.build` to create station data.",
    )
    only_rankable = st.toggle(f"Only ZIPs with ≥ {config.MIN_EVS_FOR_RANKING} EVs", value=False)

z = zips_all[zips_all["county"].isin(sel_counties)]
z_map = z[z["rankable"]] if only_rankable else z

# ---------- header ----------
st.title("Where the Bay Area is short on EV chargers")
nrel_date = meta["nrel_fetched_at"][:10]
st.caption(
    f"EV registrations: CA DMV, {meta['dmv_latest'].split()[0]} · Public chargers: NREL AFDC, "
    f"fetched {nrel_date} · {len(z)} ZIPs in {len(sel_counties)} counties"
)
if z.empty:
    st.warning("Pick at least one county.")
    st.stop()

tot_evs, tot_l2, tot_dc = z["evs_2026"].sum(), z["l2_ports"].sum(), z["dcfc_ports"].sum()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Electric vehicles", fmt_int(tot_evs))
c2.metric("Public Level 2 ports", fmt_int(tot_l2))
c3.metric("Public DC fast ports", fmt_int(tot_dc))
c4.metric("EVs per public port", fmt_ratio(tot_evs / (tot_l2 + tot_dc)) if tot_l2 + tot_dc else "–")

tab_map, tab_rank, tab_zip, tab_cty, tab_method = st.tabs(
    ["Map", "Rankings", "ZIP detail", "Counties", "Method"]
)

# ---------- map ----------
with tab_map:
    geo = build_layer_data(z_map, load_geojson(), metric)
    layers = [
        pdk.Layer(
            "GeoJsonLayer",
            geo,
            pickable=True,
            stroked=True,
            filled=True,
            get_fill_color="properties.fill",
            get_line_color="properties.line",
            get_line_width="properties.lw",
            line_width_units="pixels",
        )
    ]
    if show_stations and stations is not None:
        s = stations[stations["zip"].isin(set(z_map["zip"]))].copy()
        s["radius"] = s["ev_dc_fast_num"].gt(0).map({True: 60, False: 30})
        s["color"] = (
            s["ev_dc_fast_num"].gt(0).map({True: [33, 102, 172, 220], False: [90, 90, 90, 160]})
        )
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                s[["longitude", "latitude", "radius", "color"]],
                get_position=["longitude", "latitude"],
                get_radius="radius",
                get_fill_color="color",
                radius_min_pixels=1.5,
                pickable=False,
            )
        )
    tooltip = {
        "html": "<b>{zip}</b> · {city}, {county}<br/>"
        f"{METRICS[metric]}: <b>{{metric}}</b><br/>"
        "EVs: {evs}<br/>L2 ports: {l2} · DCFC ports: {dcfc}<br/>"
        "EVs per port: {epp}<br/>Gap rank: {rank}",
        "style": {"fontSize": "13px"},
    }
    st.pydeck_chart(
        pdk.Deck(
            layers=layers,
            map_style="light",
            tooltip=tooltip,
            initial_view_state=pdk.ViewState(latitude=37.6, longitude=-122.2, zoom=8.5),
        ),
        height=620,
    )
    st.caption(
        "Lighter → darker = bigger value. Blue outline = ZIP with no public charging ports. "
        "Grey = no data. Colour scale clipped at the 5th–95th percentile."
        + (" Dots: blue = has DC fast, grey = Level 2 only." if show_stations else "")
    )

# ---------- rankings ----------
with tab_rank:
    r = z[z["rankable"]].sort_values("gap_rank")
    table = pd.DataFrame(
        {
            "Rank": r["gap_rank"].astype(int),
            "ZIP": r["zip"],
            "City": r["city"],
            "County": r["county"],
            "EVs": r["evs_2026"],
            "BEVs": r["bevs_2026"],
            "L2 ports": r["l2_ports"],
            "DCFC ports": r["dcfc_ports"],
            "EVs per port": r["evs_per_port"],
            "2-yr EV growth": r["ev_growth_2y"] * 100,
            "Renter share": r["renter_share"] * 100,
            "Priority score": r["priority_score"],
            "Top network": r["top_network"].fillna(""),
        }
    )
    st.caption(
        f"{len(table)} ZIPs with ≥ {config.MIN_EVS_FOR_RANKING} EVs. ZIPs with zero public "
        "ports rank first (blank EVs per port). Rank is across the whole Bay Area."
    )
    st.dataframe(
        table,
        hide_index=True,
        height=560,
        column_config={
            "EVs": st.column_config.NumberColumn(format="localized"),
            "BEVs": st.column_config.NumberColumn(format="localized"),
            "L2 ports": st.column_config.NumberColumn(format="localized"),
            "DCFC ports": st.column_config.NumberColumn(format="localized"),
            "EVs per port": st.column_config.NumberColumn(format="%.1f"),
            "2-yr EV growth": st.column_config.NumberColumn(format="%.1f%%"),
            "Renter share": st.column_config.NumberColumn(format="%.0f%%"),
            "Priority score": st.column_config.NumberColumn(format="%.0f"),
        },
    )
    st.download_button(
        "Download CSV",
        table.to_csv(index=False).encode(),
        file_name="bay_area_ev_gap_rankings.csv",
        mime="text/csv",
    )

# ---------- ZIP detail ----------
with tab_zip:
    options = z.sort_values("zip")["zip"].tolist()
    default = z.sort_values("gap_rank")["zip"].iloc[0]
    if st.session_state.get("zip_select") not in options:  # county filter removed it
        st.session_state.pop("zip_select", None)
    zp = st.selectbox(
        "ZIP code",
        options,
        index=options.index(default),
        key="zip_select",
        format_func=lambda x: f"{x} · {z.set_index('zip').loc[x, 'city']}",
    )
    row = z.set_index("zip").loc[zp]
    cty = counties_all.set_index("county").loc[row["county"]]
    bay = counties_all.set_index("county").loc["Bay Area total"]

    st.subheader(f"{zp} · {row['city']}, {row['county']} County")
    if pd.isna(row["gap_rank"]):
        st.caption(f"Not ranked: fewer than {config.MIN_EVS_FOR_RANKING} EVs registered.")
    else:
        n_rank = int(zips_all["rankable"].sum())
        st.caption(
            f"Gap rank #{int(row['gap_rank'])} of {n_rank} ranked Bay Area ZIPs "
            f"(gap score {row['gap_score']:.0f}/100)."
        )

    compare = pd.DataFrame(
        {
            "Measure": [
                "EVs per public port",
                "BEVs per DC fast port",
                "2-year EV growth",
                "EV share of light-duty vehicles",
            ],
            f"ZIP {zp}": [
                fmt_ratio(row["evs_per_port"]) if not row["no_public_ports"] else "no public ports",
                fmt_ratio(row["bevs_per_dcfc"]),
                fmt_pct(row["ev_growth_2y"]),
                fmt_pct(row["ev_share"]),
            ],
            f"{row['county']} County": [
                fmt_ratio(cty["evs_per_port"]),
                fmt_ratio(cty["bevs_per_dcfc"]),
                fmt_pct(cty["ev_growth_2y"]),
                fmt_pct(cty["ev_share"]),
            ],
            "Bay Area": [
                fmt_ratio(bay["evs_per_port"]),
                fmt_ratio(bay["bevs_per_dcfc"]),
                fmt_pct(bay["ev_growth_2y"]),
                fmt_pct(bay["ev_share"]),
            ],
        }
    )
    left, right = st.columns([3, 2])
    with left:
        st.dataframe(compare, hide_index=True)
        k1, k2, k3 = st.columns(3)
        k1.metric(
            "EVs (Jan 2026)",
            fmt_int(row["evs_2026"]),
            f"{fmt_int(row['evs_2026'] - row['evs_2024'])} vs Jan 2024",
        )
        k2.metric("BEVs / PHEVs", f"{fmt_int(row['bevs_2026'])} / {fmt_int(row['phevs_2026'])}")
        k3.metric("Public stations", fmt_int(row["stations"]))
    with right:
        st.markdown("**Public ports by level**")
        st.bar_chart(
            pd.DataFrame(
                {
                    "Level": ["Level 2", "DC fast", "Level 1 (not counted)"],
                    "Ports": [row["l2_ports"], row["dcfc_ports"], row["l1_ports"]],
                }
            ),
            x="Level",
            y="Ports",
            horizontal=True,
            sort=False,
            height=180,
        )
        if stations is not None and row["stations"] > 0:
            s = stations[stations["zip"] == zp]
            nets = (
                s.assign(ports=s["ev_level2_evse_num"] + s["ev_dc_fast_num"])
                .groupby("ev_network")["ports"]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
                .rename(columns={"ev_network": "Network", "ports": "Ports"})
            )
            st.markdown("**Networks**")
            st.dataframe(nets, hide_index=True)

# ---------- counties ----------
with tab_cty:
    c = counties_all[counties_all["county"].isin(sel_counties)]
    bay_epp = counties_all.set_index("county").loc["Bay Area total", "evs_per_port"]
    st.markdown(f"**EVs per public port by county** (Bay Area: {bay_epp:.1f})")
    st.bar_chart(
        c,
        x="county",
        y="evs_per_port",
        horizontal=True,
        sort="-evs_per_port",
        x_label="EVs per public port",
        y_label="",
        height=360,
    )
    ct = pd.concat([c, counties_all[counties_all["county"] == "Bay Area total"]])
    st.dataframe(
        pd.DataFrame(
            {
                "County": ct["county"],
                "ZIPs": ct["zips"],
                "EVs": ct["evs_2026"],
                "BEVs": ct["bevs_2026"],
                "L2 ports": ct["l2_ports"],
                "DCFC ports": ct["dcfc_ports"],
                "EVs per port": ct["evs_per_port"],
                "2-yr EV growth": ct["ev_growth_2y"] * 100,
            }
        ),
        hide_index=True,
        column_config={
            "EVs": st.column_config.NumberColumn(format="localized"),
            "BEVs": st.column_config.NumberColumn(format="localized"),
            "L2 ports": st.column_config.NumberColumn(format="localized"),
            "DCFC ports": st.column_config.NumberColumn(format="localized"),
            "EVs per port": st.column_config.NumberColumn(format="%.1f"),
            "2-yr EV growth": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

# ---------- method ----------
with tab_method:
    st.markdown(f"""
### Data sources
- **EV registrations:** [CA DMV Vehicle Fuel Type Count by Zip Code](https://data.ca.gov/dataset/vehicle-fuel-type-count-by-zip-code)
  — {meta["dmv_latest"]} (latest) and {meta["dmv_baseline"]} (baseline). Light-duty only.
- **Public chargers:** [NREL Alternative Fuel Stations API](https://developer.nlr.gov/docs/transportation/alt-fuel-stations-v1/all/)
  — open, public, electric stations in California, fetched {nrel_date}.
- **Geography:** [Census 2020 ZCTA ↔ county and place relationship files](https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.html)
  and [cartographic ZCTA boundaries (1:500k)](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html).
  Each ZCTA is assigned to the county it overlaps most by land area.
- **Renters:** [Census ACS 5-year table B25003 (tenure)](https://www.census.gov/programs-surveys/acs/data/summary-file.html), by ZCTA.

### Metrics
| Metric | Definition |
|---|---|
| EVs | Battery-electric (BEV) + plug-in hybrid (PHEV) light-duty registrations |
| Public ports | Level 2 + DC fast ports at public stations (Level 1 excluded) |
| EVs per public port | EVs ÷ public ports (blank when a ZIP has zero ports) |
| BEVs per DC fast port | BEVs ÷ DC fast ports |
| 2-year EV growth | EVs Jan 2026 ÷ EVs Jan 2024 − 1 |
| EV share | EVs ÷ all light-duty vehicles |
| Gap score | Percentile (0–100) of EVs per port among ZIPs with ≥ {config.MIN_EVS_FOR_RANKING} EVs; zero-port ZIPs = 100 |
| Gap rank | 1 = biggest gap. Zero-port ZIPs first (by EV count), then by EVs per port |
| Renter share | Renter-occupied ÷ occupied housing units (ACS 5-year, table B25003) |
| Priority score | Mean of gap score and renter-share percentile (0–100): many EVs, few chargers, mostly renters |

### Limitations
- DMV registrations are a 1 Jan 2026 snapshot by owner ZIP, not where cars charge; commuters charge near work.
- NREL lists public ports; it doesn't show pricing, reliability, downtime or utilization.
- ZIP codes and Census ZCTAs don't match perfectly.
- Tesla Superchargers count as DC fast ports; many are Tesla-first, so non-Tesla drivers may see a bigger gap.
- Home and workplace charging isn't counted. Areas with many single-family homes need fewer public chargers.

Code: [github.com/pmghuwalewala/bay-area-ev-gap-map](https://github.com/pmghuwalewala/bay-area-ev-gap-map)
""")
