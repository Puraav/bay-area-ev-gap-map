"""Turn raw downloads into ZIP- and county-level charging gap metrics."""

import json

import geopandas as gpd
import numpy as np
import pandas as pd

from evgap import config


def snake(name: str) -> str:
    """Convert a column header like 'ZIP Code' to 'zip_code'."""
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def assign_zcta_to_county(rel: pd.DataFrame) -> pd.DataFrame:
    """Pick, for each ZCTA, the county with the largest land-area overlap.

    Expects columns `zip`, `county_fips`, `land_part`. Returns `zip`, `county_fips`.
    """
    rel = rel.sort_values(["zip", "land_part", "county_fips"], ascending=[True, False, True])
    return rel.drop_duplicates("zip")[["zip", "county_fips"]].reset_index(drop=True)


def load_bay_area_zips() -> pd.DataFrame:
    """Return Bay Area ZCTAs with their assigned county name."""
    rel = pd.read_csv(config.RAW_DIR / "zcta_county_rel.txt", sep="|", dtype=str)
    rel = rel.dropna(subset=["GEOID_ZCTA5_20"]).rename(
        columns={
            "GEOID_ZCTA5_20": "zip",
            "GEOID_COUNTY_20": "county_fips",
            "AREALAND_PART": "land_part",
        }
    )
    rel["land_part"] = rel["land_part"].astype("int64")
    # Assign across all counties first, so a ZCTA mostly outside the region is dropped.
    assigned = assign_zcta_to_county(rel)
    fips_to_name = {v: k for k, v in config.BAY_AREA_COUNTIES.items()}
    assigned = assigned[assigned["county_fips"].isin(fips_to_name)].copy()
    assigned["county"] = assigned["county_fips"].map(fips_to_name)
    return assigned[["zip", "county"]].sort_values("zip").reset_index(drop=True)


def load_place_names() -> pd.DataFrame:
    """Name each ZCTA after the California Census place it overlaps most (land area)."""
    rel = pd.read_csv(
        config.RAW_DIR / "zcta_place_rel.txt", sep="|", dtype=str, encoding="utf-8-sig"
    )
    rel = rel.dropna(subset=["GEOID_ZCTA5_20"])
    rel = rel[rel["GEOID_PLACE_20"].str.startswith("06")]
    rel["land_part"] = rel["AREALAND_PART"].astype("int64")
    rel = rel.sort_values(["GEOID_ZCTA5_20", "land_part"], ascending=[True, False])
    rel = rel.drop_duplicates("GEOID_ZCTA5_20")
    name = rel["NAMELSAD_PLACE_20"].str.replace(r" (city|town|CDP)$", "", regex=True)
    return pd.DataFrame({"zip": rel["GEOID_ZCTA5_20"], "city": name})


def filter_dmv(df: pd.DataFrame) -> pd.DataFrame:
    """Keep light-duty rows with 5-digit ZIPs. Expects snake_case columns."""
    df = df[df["duty"].str.strip().str.lower() == "light"]
    df = df[df["zip_code"].astype(str).str.fullmatch(r"\d{5}")]
    return df


def dmv_per_zip(path) -> pd.DataFrame:
    """Aggregate a DMV file to BEVs, PHEVs, EVs and all light-duty vehicles per ZIP."""
    raw = pd.read_csv(path, dtype=str)
    mapping = {c: snake(c) for c in raw.columns}
    df = filter_dmv(raw.rename(columns=mapping))
    df["vehicles"] = pd.to_numeric(df["vehicles"], errors="coerce").fillna(0).astype("int64")
    df = df.rename(columns={"zip_code": "zip"})
    out = (
        pd.DataFrame(
            {
                "bevs": df[df["fuel"] == "Battery Electric"].groupby("zip")["vehicles"].sum(),
                "phevs": df[df["fuel"] == "Plug-in Hybrid"].groupby("zip")["vehicles"].sum(),
                "all_vehicles": df.groupby("zip")["vehicles"].sum(),
            }
        )
        .fillna(0)
        .astype("int64")
    )
    out["evs"] = out["bevs"] + out["phevs"]
    return out.reset_index()


def load_zcta_shapes(zips: pd.Series) -> gpd.GeoDataFrame:
    """Load 2020 ZCTA polygons for the given ZIPs (EPSG:4326)."""
    shapes = gpd.read_file(f"zip://{config.RAW_DIR / 'zcta_2020_500k.zip'}")
    shapes = shapes.rename(columns={"ZCTA5CE20": "zip"})[["zip", "geometry"]]
    return shapes[shapes["zip"].isin(set(zips))].to_crs(4326).reset_index(drop=True)


def load_stations(shapes: gpd.GeoDataFrame) -> tuple[pd.DataFrame, dict]:
    """Load NREL stations, repair bad ZIPs by point-in-polygon, keep Bay Area rows."""
    data = json.loads((config.RAW_DIR / "afdc_ca_elec.json").read_text())
    st = pd.DataFrame(data["fuel_stations"])
    cols = [
        "id",
        "station_name",
        "city",
        "zip",
        "ev_level2_evse_num",
        "ev_dc_fast_num",
        "ev_level1_evse_num",
        "ev_network",
        "latitude",
        "longitude",
        "facility_type",
    ]
    st = st[cols].copy()
    for c in ["ev_level2_evse_num", "ev_dc_fast_num", "ev_level1_evse_num"]:
        st[c] = pd.to_numeric(st[c], errors="coerce").fillna(0).astype("int64")
    st["ev_network"] = st["ev_network"].fillna("Unknown")
    st["zip"] = st["zip"].fillna("").astype(str).str.strip().str[:5]
    bad = ~st["zip"].str.fullmatch(r"\d{5}")

    # Point-in-polygon fallback against Bay Area ZCTAs.
    stats = {"stations_ca": len(st), "needed_pip": int(bad.sum()), "pip_matched": 0}
    if bad.any():
        pts = gpd.GeoDataFrame(
            st[bad],
            geometry=gpd.points_from_xy(st.loc[bad, "longitude"], st.loc[bad, "latitude"]),
            crs=4326,
        )
        hit = gpd.sjoin(pts, shapes.rename(columns={"zip": "zip_pip"}), predicate="within")
        hit = hit[~hit.index.duplicated()]
        st.loc[hit.index, "zip"] = hit["zip_pip"]
        stats["pip_matched"] = len(hit)
    # Stations with a bad ZIP that fall outside Bay Area shapes are simply outside the region.
    # "Unmatched" = bad-ZIP stations whose coordinates sit in the Bay Area bounding box
    # but in no ZCTA polygon (e.g. on water).
    minx, miny, maxx, maxy = shapes.total_bounds
    still_bad = ~st["zip"].str.fullmatch(r"\d{5}")
    in_box = st["longitude"].between(minx, maxx) & st["latitude"].between(miny, maxy)
    stats["unmatched_in_region"] = int((still_bad & in_box).sum())

    bay = st[st["zip"].isin(set(shapes["zip"]))].copy()
    stats["stations_bay_area"] = len(bay)
    return bay.reset_index(drop=True), stats


def stations_per_zip(st: pd.DataFrame) -> pd.DataFrame:
    """Aggregate station rows to port counts, top network and city per ZIP."""
    st = st.assign(
        ports=st["ev_level2_evse_num"] + st["ev_dc_fast_num"],
        tesla_dcfc=np.where(
            st["ev_network"].str.contains("Tesla", case=False), st["ev_dc_fast_num"], 0
        ),
    )
    g = st.groupby("zip")
    out = pd.DataFrame(
        {
            "stations": g.size(),
            "l2_ports": g["ev_level2_evse_num"].sum(),
            "dcfc_ports": g["ev_dc_fast_num"].sum(),
            "l1_ports": g["ev_level1_evse_num"].sum(),
            "tesla_dcfc_ports": g["tesla_dcfc"].sum(),
        }
    )
    net = st.groupby(["zip", "ev_network"])["ports"].sum().reset_index()
    net = net.sort_values(["zip", "ports", "ev_network"], ascending=[True, False, True])
    out["top_network"] = net.drop_duplicates("zip").set_index("zip")["ev_network"]
    return out.reset_index()


def compute_metrics(df: pd.DataFrame, min_evs: int = config.MIN_EVS_FOR_RANKING) -> pd.DataFrame:
    """Add ratio, ranking and gap-score columns to a joined ZIP table."""
    df = df.copy()
    df["public_ports"] = df["l2_ports"] + df["dcfc_ports"]
    df["no_public_ports"] = df["public_ports"] == 0
    ports = df["public_ports"].replace(0, np.nan)
    df["evs_per_port"] = df["evs_2026"] / ports
    df["bevs_per_dcfc"] = df["bevs_2026"] / df["dcfc_ports"].replace(0, np.nan)
    df["ev_growth_2y"] = df["evs_2026"] / df["evs_2024"].replace(0, np.nan) - 1
    df["ev_share"] = df["evs_2026"] / df["all_vehicles_2026"].replace(0, np.nan)
    df["rankable"] = df["evs_2026"] >= min_evs

    r = df["rankable"]
    score = df.loc[r, "evs_per_port"].rank(pct=True) * 100
    score[df.loc[r, "no_public_ports"]] = 100.0
    df["gap_score"] = np.nan
    df.loc[r, "gap_score"] = score

    # Rank: zero-port ZIPs first (more EVs = bigger gap), then by EVs per port.
    zero = df[r & df["no_public_ports"]].sort_values("evs_2026", ascending=False)
    rest = df[r & ~df["no_public_ports"]].sort_values("evs_per_port", ascending=False)
    ranked = list(zero.index) + list(rest.index)
    df["gap_rank"] = pd.Series(range(1, len(ranked) + 1), index=ranked, dtype="Int64")
    return df


def county_summary(z: pd.DataFrame) -> pd.DataFrame:
    """Sum ZIP counts to counties and add a Bay Area total row."""
    cols = [
        "evs_2026",
        "bevs_2026",
        "phevs_2026",
        "evs_2024",
        "l2_ports",
        "dcfc_ports",
        "public_ports",
        "tesla_dcfc_ports",
        "all_vehicles_2026",
    ]
    c = z.groupby("county")[cols].sum()
    c.loc["Bay Area total"] = c.sum()
    c["evs_per_port"] = c["evs_2026"] / c["public_ports"]
    c["bevs_per_dcfc"] = c["bevs_2026"] / c["dcfc_ports"]
    c["ev_growth_2y"] = c["evs_2026"] / c["evs_2024"] - 1
    c["ev_share"] = c["evs_2026"] / c["all_vehicles_2026"]
    c["zips"] = z.groupby("county").size()
    c.loc["Bay Area total", "zips"] = len(z)
    c["zips"] = c["zips"].astype(int)
    return c.reset_index()


def write_geojson(shapes: gpd.GeoDataFrame) -> None:
    """Write simplified Bay Area ZCTA polygons for the app and charts."""
    simple = shapes.copy()
    simple["geometry"] = simple.geometry.simplify(config.GEOJSON_TOLERANCE, preserve_topology=True)
    simple.to_file(config.PROCESSED_DIR / "bay_area_zcta.geojson", driver="GeoJSON")


def main() -> None:
    """Build all processed outputs and print sanity summaries."""
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    zips = load_bay_area_zips()
    print(f"Bay Area ZCTAs: {len(zips)}")

    latest = dmv_per_zip(config.RAW_DIR / "dmv_latest.csv").add_suffix("_2026")
    base = dmv_per_zip(config.RAW_DIR / "dmv_baseline.csv").add_suffix("_2024")
    latest = latest.rename(columns={"zip_2026": "zip"})
    base = base.rename(columns={"zip_2024": "zip"})[["zip", "evs_2024"]]

    shapes = load_zcta_shapes(zips["zip"])
    stations, st_stats = load_stations(shapes)
    ports = stations_per_zip(stations)
    print(
        f"Stations: {st_stats['stations_ca']:,} CA; {st_stats['needed_pip']} had no valid "
        f"ZIP, {st_stats['pip_matched']} fixed by point-in-polygon, "
        f"{st_stats['unmatched_in_region']} unmatched in region; "
        f"{st_stats['stations_bay_area']:,} in Bay Area"
    )

    z = zips.merge(load_place_names(), on="zip", how="left")
    z = z.merge(latest, on="zip", how="left").merge(base, on="zip", how="left")
    z = z.merge(ports, on="zip", how="left")
    count_cols = [
        "bevs_2026",
        "phevs_2026",
        "all_vehicles_2026",
        "evs_2026",
        "evs_2024",
        "stations",
        "l2_ports",
        "dcfc_ports",
        "l1_ports",
        "tesla_dcfc_ports",
    ]
    z[count_cols] = z[count_cols].fillna(0).astype("int64")
    z["top_network"] = z["top_network"].fillna("")
    z["city"] = z["city"].fillna(z["county"])  # unincorporated ZCTAs: fall back to county
    z = compute_metrics(z)

    cols = [
        "zip",
        "city",
        "county",
        "evs_2026",
        "bevs_2026",
        "phevs_2026",
        "evs_2024",
        "all_vehicles_2026",
        "stations",
        "l2_ports",
        "dcfc_ports",
        "l1_ports",
        "tesla_dcfc_ports",
        "public_ports",
        "no_public_ports",
        "top_network",
        "evs_per_port",
        "bevs_per_dcfc",
        "ev_growth_2y",
        "ev_share",
        "rankable",
        "gap_score",
        "gap_rank",
    ]
    z = z[cols]
    z.to_parquet(config.PROCESSED_DIR / "zip_metrics.parquet", index=False)
    z.to_csv(config.PROCESSED_DIR / "zip_metrics.csv", index=False)
    counties = county_summary(z)
    counties.to_csv(config.PROCESSED_DIR / "county_metrics.csv", index=False)
    stations.to_parquet(config.PROCESSED_DIR / "stations_bay_area.parquet", index=False)
    write_geojson(shapes)

    dmv = json.loads((config.RAW_DIR / "dmv_sources.json").read_text())
    afdc = json.loads((config.RAW_DIR / "afdc_meta.json").read_text())
    meta = {
        "dmv_latest": dmv["latest"],
        "dmv_baseline": dmv["baseline"],
        "nrel_fetched_at": afdc["fetched_at"],
        "zip_rows": len(z),
        "rankable_zips": int(z["rankable"].sum()),
        **st_stats,
    }
    (config.PROCESSED_DIR / "build_meta.json").write_text(json.dumps(meta, indent=2))

    t = counties.set_index("county").loc["Bay Area total"]
    print(
        f"\nBay Area: {t.evs_2026:,.0f} EVs ({t.bevs_2026:,.0f} BEV / {t.phevs_2026:,.0f} PHEV), "
        f"{t.l2_ports:,.0f} public L2 + {t.dcfc_ports:,.0f} DCFC ports, "
        f"{t.evs_per_port:.1f} EVs per public port\n"
    )
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(
            counties[
                [
                    "county",
                    "zips",
                    "evs_2026",
                    "bevs_2026",
                    "l2_ports",
                    "dcfc_ports",
                    "evs_per_port",
                    "ev_growth_2y",
                ]
            ]
            .round(2)
            .to_string(index=False)
        )
        top = z[z["rankable"]].sort_values("gap_rank").head(15)
        print("\nTop 15 ZIPs by gap_score:")
        print(
            top[
                [
                    "gap_rank",
                    "zip",
                    "city",
                    "county",
                    "evs_2026",
                    "public_ports",
                    "evs_per_port",
                    "gap_score",
                ]
            ]
            .round(1)
            .to_string(index=False)
        )
    zero = z[z["rankable"] & z["no_public_ports"]]
    print(f"\nRankable ZIPs with zero public ports: {len(zero)} ({zero['evs_2026'].sum():,} EVs)")


if __name__ == "__main__":
    main()
