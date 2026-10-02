"""Paths and constants for the evgap pipeline."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
CHARTS_DIR = ROOT / "charts"

BAY_AREA_COUNTIES: dict[str, str] = {
    "Alameda": "06001",
    "Contra Costa": "06013",
    "Marin": "06041",
    "Napa": "06055",
    "San Francisco": "06075",
    "San Mateo": "06081",
    "Santa Clara": "06085",
    "Solano": "06095",
    "Sonoma": "06097",
}

MIN_EVS_FOR_RANKING = 200

DMV_LATEST_LABEL = "1/1/2026"
DMV_BASELINE_LABEL = "1/1/2024"

EV_FUELS = {"Battery Electric", "Plug-in Hybrid"}
GEOJSON_TOLERANCE = 0.0005  # degrees, for the simplified ZCTA GeoJSON

# ACS 5-year tenure table (B25003), newest vintage first. The Census API now needs a key,
# so we use the keyless table-based summary file on www2.census.gov instead.
ACS_YEARS = [2024, 2023]
ACS_URL = (
    "https://www2.census.gov/programs-surveys/acs/summary_file/{year}/table-based-SF/"
    "data/5YRData/acsdt5y{year}-b25003.dat"
)
