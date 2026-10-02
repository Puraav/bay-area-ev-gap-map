"""Download every raw input into data/raw/."""

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from evgap import config

CKAN_URL = "https://data.ca.gov/api/3/action/package_show?id=vehicle-fuel-type-count-by-zip-code"
# NREL is now the National Laboratory of the Rockies; the API host moved to nlr.gov.
NREL_URL = "https://developer.nlr.gov/api/alt-fuel-stations/v1.json"
ZCTA_REL_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/"
    "tab20_zcta520_county20_natl.txt"
)
ZCTA_PLACE_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_place20_natl.txt"
)
ZCTA_SHP_URL = "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_zcta520_500k.zip"
TIMEOUT = 120


def download(url: str, dest: Path, force: bool = False) -> bool:
    """Stream `url` to `dest`. Return True if downloaded, False if skipped."""
    if dest.exists() and not force:
        print(f"  skip {dest.name} (exists)")
        return False
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=TIMEOUT) as r:
        r.raise_for_status()
        done, next_report = 0, 10
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                done += len(chunk)
                if done / 1e6 >= next_report:
                    print(f"  {dest.name}: {done / 1e6:.0f} MB", flush=True)
                    next_report += 10
    tmp.rename(dest)
    print(f"  saved {dest.name} ({done / 1e6:.1f} MB)")
    return True


def _label_date(name: str) -> datetime | None:
    """Parse the leading M/D/YYYY date from a DMV resource name."""
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", name)
    return datetime(int(m[3]), int(m[1]), int(m[2])) if m else None


def fetch_dmv(force: bool = False) -> dict[str, str]:
    """Download the latest and baseline DMV files chosen via the CKAN API."""
    resources = requests.get(CKAN_URL, timeout=TIMEOUT).json()["result"]["resources"]
    dated = [(r, _label_date(r["name"])) for r in resources if r.get("format") == "CSV"]
    dated = [(r, d) for r, d in dated if d]

    def pick(label: str, fallback_latest: bool) -> dict:
        for r, _ in dated:
            if label in r["name"]:
                return r
        if not fallback_latest:
            sys.exit(f"DMV resource for {label} not found")
        r = max(dated, key=lambda x: x[1])[0]
        print(f"WARNING: {label} not found; using most recent: {r['name']}")
        return r

    latest = pick(config.DMV_LATEST_LABEL, fallback_latest=True)
    baseline = pick(config.DMV_BASELINE_LABEL, fallback_latest=False)
    download(latest["url"], config.RAW_DIR / "dmv_latest.csv", force)
    download(baseline["url"], config.RAW_DIR / "dmv_baseline.csv", force)
    sources = {
        "latest": latest["name"],
        "baseline": baseline["name"],
        "latest_url": latest["url"],
        "baseline_url": baseline["url"],
    }
    (config.RAW_DIR / "dmv_sources.json").write_text(json.dumps(sources, indent=2))
    return sources


def fetch_nrel(force: bool = False) -> None:
    """Download all public, open CA EV stations from the NREL AFDC API."""
    dest = config.RAW_DIR / "afdc_ca_elec.json"
    if dest.exists() and not force:
        print(f"  skip {dest.name} (exists)")
        return
    load_dotenv(config.ROOT / ".env")
    key = os.getenv("NREL_API_KEY")
    if not key:
        sys.exit("NREL_API_KEY missing: copy .env.example to .env and set it")
    params = {
        "api_key": key,
        "fuel_type": "ELEC",
        "state": "CA",
        "status": "E",
        "access": "public",
        "limit": "all",
    }
    r = requests.get(NREL_URL, params=params, timeout=300)
    if r.status_code != 200:
        print(f"NREL error {r.status_code}: {r.text[:1000]}")
        sys.exit(1)
    dest.write_bytes(r.content)
    meta = {
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "params": {k: v for k, v in params.items() if k != "api_key"},
    }
    (config.RAW_DIR / "afdc_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"  saved {dest.name} ({len(r.content) / 1e6:.1f} MB)")


def summarize() -> None:
    """Print row counts and sanity checks for every raw file."""
    sources = json.loads((config.RAW_DIR / "dmv_sources.json").read_text())
    for key, label in [("latest", "DMV latest:  "), ("baseline", "DMV baseline:")]:
        df = pd.read_csv(config.RAW_DIR / f"dmv_{key}.csv", dtype=str)
        fuel_col = next(c for c in df.columns if "fuel" in c.lower())
        fuels = set(df[fuel_col].unique())
        ok = {"Battery Electric", "Plug-in Hybrid"} <= fuels
        print(
            f"{label} {sources[key].split()[0]} file, {len(df):,} rows; "
            f"columns={list(df.columns)}; BEV+PHEV present={ok}"
        )
    afdc = json.loads((config.RAW_DIR / "afdc_ca_elec.json").read_text())
    meta = json.loads((config.RAW_DIR / "afdc_meta.json").read_text())
    print(
        f"NREL:          {len(afdc['fuel_stations']):,} public CA EV stations "
        f"(fetched {meta['fetched_at']})"
    )
    rel = pd.read_csv(config.RAW_DIR / "zcta_county_rel.txt", sep="|", dtype=str)
    print(f"ZCTA rel:      {len(rel):,} rows")
    size = (config.RAW_DIR / "zcta_2020_500k.zip").stat().st_size / 1e6
    print(f"ZCTA shapes:   {size:.0f} MB")


def main() -> None:
    """Fetch all raw data, then print a summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-download existing files")
    args = parser.parse_args()
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("DMV (data.ca.gov)...")
    fetch_dmv(args.force)
    print("NREL AFDC...")
    fetch_nrel(args.force)
    print("Census ZCTA relationship file...")
    download(ZCTA_REL_URL, config.RAW_DIR / "zcta_county_rel.txt", args.force)
    print("Census ZCTA place relationship file (for city names)...")
    download(ZCTA_PLACE_URL, config.RAW_DIR / "zcta_place_rel.txt", args.force)
    print("Census ZCTA shapes...")
    download(ZCTA_SHP_URL, config.RAW_DIR / "zcta_2020_500k.zip", args.force)
    print()
    summarize()


if __name__ == "__main__":
    main()
