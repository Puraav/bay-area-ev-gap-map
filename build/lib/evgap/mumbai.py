"""San Francisco vs Mumbai: EVs and public chargers, city level (spec 09)."""

import argparse
import json
import re
import time
from datetime import UTC, datetime

import openpyxl
import pandas as pd
import requests
from shapely.geometry import Point, shape
from shapely.ops import unary_union

from evgap import config

UA = {"User-Agent": config.HTTP_USER_AGENT}
CITIES = ["San Francisco", "Mumbai"]


# ---------- fetch ----------
def fetch_boundaries(force: bool = False) -> dict:
    """City boundary polygons from Nominatim (one request per OSM relation)."""
    path = config.MUMBAI_RAW_DIR / "osm_boundaries.json"
    if path.exists() and not force:
        return json.loads(path.read_text())
    out = {}
    for city, rels in config.OSM_RELATIONS.items():
        feats = []
        for rid in rels:
            r = requests.get(
                "https://nominatim.openstreetmap.org/lookup",
                params={"osm_ids": f"R{rid}", "format": "geojson", "polygon_geojson": 1},
                headers=UA,
                timeout=60,
            )
            r.raise_for_status()
            feats.append(r.json()["features"][0])
            time.sleep(1.1)  # Nominatim usage policy: max 1 request per second
        out[city] = feats
    path.write_text(json.dumps(out))
    return out


def overpass(query: str, tries: int = 4) -> dict:
    """Run an Overpass query, cycling through endpoints with backoff on overload."""
    last = None
    for attempt in range(tries):
        for ep in config.OVERPASS_ENDPOINTS:
            try:
                r = requests.post(ep, data={"data": query}, headers=UA, timeout=200)
                if r.status_code == 200:
                    return r.json()
                last = f"{ep}: HTTP {r.status_code}"
            except (requests.RequestException, ValueError) as e:
                last = f"{ep}: {type(e).__name__}"
        wait = 20 * (attempt + 1)
        print(f"  Overpass busy ({last}); retrying in {wait}s")
        time.sleep(wait)
    raise SystemExit(f"Overpass failed after {tries} rounds: {last}")


def tiles(bbox: tuple[float, float, float, float], n: int) -> list[tuple]:
    """Split a (south, west, north, east) box into n×n smaller boxes."""
    s, w, nn, e = bbox
    dy, dx = (nn - s) / n, (e - w) / n
    return [
        (s + i * dy, w + j * dx, s + (i + 1) * dy, w + (j + 1) * dx)
        for i in range(n)
        for j in range(n)
    ]


def fetch_chargers(boundaries: dict, force: bool = False) -> dict:
    """OSM amenity=charging_station elements per city, fetched by bbox tiles."""
    path = config.MUMBAI_RAW_DIR / "osm_chargers.json"
    if path.exists() and not force:
        return json.loads(path.read_text())
    out = {"fetched_at": datetime.now(UTC).isoformat(timespec="seconds"), "cities": {}}
    for city, feats in boundaries.items():
        w, s, e, n = unary_union([shape(f["geometry"]) for f in feats]).bounds
        seen = {}
        for box in tiles((s, w, n, e), 2):
            q = (
                '[out:json][timeout:120];nwr["amenity"="charging_station"]'
                f"({box[0]},{box[1]},{box[2]},{box[3]});out center tags;"
            )
            for el in overpass(q)["elements"]:
                seen[f"{el['type']}/{el['id']}"] = el
            time.sleep(2)
        out["cities"][city] = list(seen.values())
        print(f"  {city}: {len(seen)} OSM charging stations in bounding box")
    path.write_text(json.dumps(out))
    return out


def fetch_sf_population(force: bool = False) -> dict:
    """San Francisco County population from the ACS 5-year table B01003 (keyless file)."""
    path = config.MUMBAI_RAW_DIR / "sf_population.json"
    if path.exists() and not force:
        return json.loads(path.read_text())
    for year in config.ACS_YEARS:
        url = config.ACS_POP_URL.format(year=year)
        r = requests.get(url, timeout=300)
        if r.status_code != 200:
            continue
        for line in r.text.splitlines():
            if line.startswith(config.SF_COUNTY_GEOID + "|"):
                pop = {"population": int(line.split("|")[1]), "year": year, "source": url}
                path.write_text(json.dumps(pop, indent=2))
                return pop
    raise SystemExit("SF population not found in ACS B01003")


# ---------- parse ----------
def to_int(x) -> int:
    """Parse Vahan numbers, which use Indian digit grouping ('7,47,831')."""
    if x is None or str(x).strip() == "":
        return 0
    return int(str(x).replace(",", "").strip())


def parse_vahan(path) -> pd.DataFrame:
    """Read one Vahan 'Vehicle Class Wise Fuel Data' export into long form."""
    wb = openpyxl.load_workbook(path, read_only=True)
    rows = [
        r for r in wb.worksheets[0].iter_rows(values_only=True) if any(c is not None for c in r)
    ]
    title = str(rows[0][0])
    m = re.search(r"-\s*(MH\d+)\s*,", title)
    if not m or "Till Today" not in title:
        raise ValueError(f"{path.name}: expected a 'Till Today' RTO export, got {title!r}")
    fuels = [str(c).strip() if c else "" for c in rows[2]]
    recs = []
    for r in rows[3:]:
        vclass = str(r[1]).strip()
        for fuel, val in zip(fuels[2:-1], r[2:-1], strict=True):
            n = to_int(val)
            if n:
                recs.append({"rto": m[1], "vehicle_class": vclass, "fuel": fuel, "vehicles": n})
        stated = to_int(r[-1])
        if sum(x["vehicles"] for x in recs if x["vehicle_class"] == vclass) != stated:
            raise ValueError(f"{path.name}: {vclass} fuel columns don't sum to TOTAL {stated}")
    return pd.DataFrame(recs)


def load_vahan() -> pd.DataFrame:
    """All Mumbai RTO exports, with an EV flag and vehicle segment."""
    df = pd.concat([parse_vahan(p) for p in sorted(config.MUMBAI_RAW_DIR.glob("vahan_*.xlsx"))])
    seg = {c: s for s, classes in config.VAHAN_SEGMENTS.items() for c in classes}
    df["segment"] = df["vehicle_class"].map(seg).fillna("other")
    df["is_ev"] = df["fuel"].isin(config.VAHAN_EV_FUELS)
    return df


def station_ports(tags: dict) -> tuple[int, bool]:
    """(ports, is_dc_fast) for one OSM charging station from its capacity/socket tags."""
    sockets = {}
    for k, v in tags.items():
        parts = k.split(":")
        if len(parts) == 2 and parts[0] == "socket" and str(v).isdigit():
            sockets[parts[1]] = int(v)
    if str(tags.get("capacity", "")).isdigit():
        ports = int(tags["capacity"])
    else:
        ports = sum(sockets.values()) or 1
    dc = any(s in config.DC_SOCKETS for s in sockets)
    for k, v in tags.items():
        if k.startswith("socket:") and k.endswith(":output"):
            kw = re.match(r"\s*([\d.]+)\s*kW", str(v), re.I)
            if kw and float(kw[1]) >= config.DC_MIN_KW:
                dc = True
    return max(ports, 1), dc


def chargers_in_city(elements: list[dict], feats: list[dict]) -> pd.DataFrame:
    """Keep OSM stations inside the city boundary; add ports, DC flag and operator."""
    poly = unary_union([shape(f["geometry"]) for f in feats])
    recs = []
    for el in elements:
        lat = el.get("lat", el.get("center", {}).get("lat"))
        lon = el.get("lon", el.get("center", {}).get("lon"))
        if lat is None or not poly.contains(Point(lon, lat)):
            continue
        tags = el.get("tags", {})
        if tags.get("access") in {"private", "no", "customers"}:
            continue  # public charging only, as with NREL
        ports, dc = station_ports(tags)
        op = tags.get("operator") or tags.get("network") or tags.get("brand") or "Unknown"
        recs.append({"lat": lat, "lon": lon, "ports": ports, "dc_fast": dc, "operator": op})
    return pd.DataFrame(recs, columns=["lat", "lon", "ports", "dc_fast", "operator"])


# ---------- compare ----------
def compare(vahan: pd.DataFrame, osm: dict, bounds: dict, sf_pop: dict) -> dict:
    """Build the city comparison from parsed inputs."""
    zips = pd.read_csv(config.PROCESSED_DIR / "zip_metrics.csv", dtype={"zip": str})
    sf = zips[zips["county"] == "San Francisco"]
    ev = vahan[vahan["is_ev"]]
    seg = ev.groupby("segment")["vehicles"].sum()
    cars_all = vahan[vahan["segment"] == "car"]["vehicles"].sum()

    st = {c: chargers_in_city(osm["cities"][c], bounds[c]) for c in CITIES}
    nrel_ports = int(sf["public_ports"].sum())
    coverage = st["San Francisco"]["ports"].sum() / nrel_ports

    def city(name: str, ev_cars: int, pop: int, extra: dict) -> dict:
        s = st[name]
        ports = int(s["ports"].sum())
        ops = s.groupby("operator")["ports"].sum().sort_values(ascending=False).head(5)
        return {
            "ev_cars": int(ev_cars),
            "population": int(pop),
            "osm_stations": len(s),
            "osm_ports": ports,
            "ev_cars_per_osm_port": round(ev_cars / ports, 1) if ports else None,
            "osm_ports_per_100k": round(ports / pop * 1e5, 2),
            "dc_fast_station_share": round(s["dc_fast"].mean(), 3) if len(s) else None,
            "top_operators": {k: int(v) for k, v in ops.items()},
            **extra,
        }

    mum_ev_cars = int(seg.get("car", 0))
    mum_pop = sum(config.MUMBAI_POPULATION_2011.values())
    mumbai = city(
        "Mumbai",
        mum_ev_cars,
        mum_pop,
        {
            "population_year": 2011,
            "rtos": sorted(vahan["rto"].unique()),
            "ev_two_wheelers": int(seg.get("two_wheeler", 0)),
            "ev_three_wheelers": int(seg.get("three_wheeler", 0)),
            "ev_other": int(seg.get("other", 0)),
            "ev_share_of_cars": round(mum_ev_cars / cars_all, 4),
            # Sensitivity, clearly an estimate: if OSM misses Mumbai chargers at SF's rate.
            "ev_cars_per_port_if_osm_coverage_like_sf": None,
        },
    )
    if mumbai["osm_ports"]:
        est_ports = mumbai["osm_ports"] / coverage
        mumbai["ev_cars_per_port_if_osm_coverage_like_sf"] = round(mum_ev_cars / est_ports, 1)
    sfc = city(
        "San Francisco",
        int(sf["evs_2026"].sum()),
        sf_pop["population"],
        {
            "population_year": f"ACS {sf_pop['year'] - 4}-{sf_pop['year']}",
            "nrel_ports": nrel_ports,
            "nrel_stations": int(sf["stations"].sum()),
            "ev_cars_per_nrel_port": round(sf["evs_2026"].sum() / nrel_ports, 1),
            "nrel_ports_per_100k": round(nrel_ports / sf_pop["population"] * 1e5, 2),
            "ev_share_of_cars": round(sf["evs_2026"].sum() / sf["all_vehicles_2026"].sum(), 4),
        },
    )
    return {
        "San Francisco": sfc,
        "Mumbai": mumbai,
        "data_access": {
            "sf_geo_units": int(len(sf)),
            "sf_people_per_unit": round(sf_pop["population"] / len(sf)),
            "mumbai_geo_units": int(vahan["rto"].nunique()),
            "mumbai_people_per_unit": round(mum_pop / vahan["rto"].nunique()),
            "resolution_ratio": round(
                (mum_pop / vahan["rto"].nunique()) / (sf_pop["population"] / len(sf))
            ),
            "sf_official_charger_stations": int(sf["stations"].sum()),
            "mumbai_open_charger_stations": len(st["Mumbai"]),
        },
        "osm_coverage_sf": round(coverage, 3),
        "osm_fetched_at": osm["fetched_at"],
        "notes": {
            "ev_cars": "SF: DMV light-duty BEV+PHEV registered 1 Jan 2026. Mumbai: Vahan "
            "cumulative registrations (Till Today) of electric/PHEV motor cars + motor cabs; "
            "not net of scrapped vehicles.",
            "ports": "OpenStreetMap amenity=charging_station inside the city boundary, "
            "public only; ports = capacity tag, else socket counts, else 1.",
        },
    }


def summary_table(c: dict) -> pd.DataFrame:
    """Side-by-side 'what can you actually find out' table (app, README, terminal)."""
    s, m, d = c["San Francisco"], c["Mumbai"], c["data_access"]
    rows = [
        (
            "EV counts: smallest area published",
            f"ZIP code ({d['sf_geo_units']} in SF)",
            f"RTO ({d['mumbai_geo_units']} in Mumbai)",
        ),
        (
            "People per smallest area",
            f"{d['sf_people_per_unit']:,}",
            f"{d['mumbai_people_per_unit']:,}",
        ),
        (
            "How you get EV counts",
            "Open CSV + API (data.ca.gov)",
            "Manual Excel export per RTO (Vahan dashboard)",
        ),
        (
            "Official public-charger list",
            f"Yes: NREL API, {d['sf_official_charger_stations']:,} stations with port counts",
            "None found",
        ),
        (
            "Best open charger list",
            f"OpenStreetMap: {s['osm_stations']:,} stations",
            f"OpenStreetMap: {m['osm_stations']:,} stations",
        ),
        ("Latest official population", s["population_year"], f"Census {m['population_year']}"),
        ("EV cars (BEV + PHEV)", f"{s['ev_cars']:,}", f"{m['ev_cars']:,}"),
        (
            "EV share of registered cars",
            f"{s['ev_share_of_cars']:.1%}",
            f"{m['ev_share_of_cars']:.1%}",
        ),
        ("EV two-wheelers", "–", f"{m['ev_two_wheelers']:,}"),
        ("EV three-wheelers", "–", f"{m['ev_three_wheelers']:,}"),
    ]
    return pd.DataFrame(rows, columns=["", "San Francisco", "Mumbai"])


def main() -> None:
    """Fetch (cached), compare, save city_comparison.{json,csv} and print the table."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-fetch OSM and ACS data")
    args = parser.parse_args()
    config.MUMBAI_RAW_DIR.mkdir(parents=True, exist_ok=True)

    vahan = load_vahan()
    missing = set(config.MUMBAI_RTOS) - set(vahan["rto"])
    print(
        f"Vahan RTOs: {sorted(vahan['rto'].unique())}"
        + (f"  MISSING: {missing}" if missing else "")
    )
    print("OSM boundaries + chargers, ACS population...")
    bounds = fetch_boundaries(args.force)
    osm = fetch_chargers(bounds, args.force)
    pop = fetch_sf_population(args.force)

    c = compare(vahan, osm, bounds, pop)
    (config.PROCESSED_DIR / "city_comparison.json").write_text(json.dumps(c, indent=2))
    t = summary_table(c)
    t.to_csv(config.PROCESSED_DIR / "city_comparison.csv", index=False)

    print()
    print(t.to_string(index=False))
    d = c["data_access"]
    print(
        f"\nResolution: one Mumbai RTO covers ~{d['resolution_ratio']}x as many people as one SF ZIP."
        f"\nOSM coverage check (SF): OSM has {c['osm_coverage_sf']:.0%} of NREL's public ports."
    )
    print(f"Top Mumbai operators (ports, OSM): {c['Mumbai']['top_operators']}")


if __name__ == "__main__":
    main()
