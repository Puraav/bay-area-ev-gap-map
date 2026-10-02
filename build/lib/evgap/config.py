"""Paths and constants for the evgap pipeline."""

from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[2]
# From a source checkout (editable install, tests, CI) use the repo root. When installed as a
# regular package (e.g. Streamlit Cloud's `pip install .`), this file lives in site-packages, so
# fall back to the working directory, which is the repo root when running the app.
ROOT = _SOURCE_ROOT if (_SOURCE_ROOT / "pyproject.toml").exists() else Path.cwd()
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

GITHUB_URL = "github.com/Puraav/bay-area-ev-gap-map"  # chart footers and app links

# --- SF vs Mumbai (spec 09) ---
MUMBAI_RAW_DIR = RAW_DIR / "mumbai"
# Vahan "Vehicle Class Wise Fuel Data", Till Today, one export per Greater Mumbai RTO.
MUMBAI_RTOS = {
    "MH1": "Mumbai Central",
    "MH2": "Mumbai West (Andheri)",
    "MH3": "Mumbai East (Wadala)",
    "MH47": "Borivali",
}
VAHAN_EV_FUELS = {"ELECTRIC(BOV)", "PURE EV", "PLUG-IN HYBRID EV"}  # strong hybrids don't plug in
VAHAN_SEGMENTS = {
    "car": ["MOTOR CAR", "MOTOR CAB"],
    "two_wheeler": [
        "M-CYCLE/SCOOTER",
        "MOPED",
        "MOTORISED CYCLE (CC > 25CC)",
        "MOTOR CYCLE/SCOOTER-USED FOR HIRE",
    ],
    "three_wheeler": [
        "THREE WHEELER (PASSENGER)",
        "THREE WHEELER (GOODS)",
        "E-RICKSHAW(P)",
        "E-RICKSHAW WITH CART (G)",
    ],
}
# OSM relations: Mumbai City + Mumbai Suburban districts (= Greater Mumbai), San Francisco.
OSM_RELATIONS = {"Mumbai": [7964376, 7964375], "San Francisco": [111968]}
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
HTTP_USER_AGENT = "bay-area-ev-gap-map/0.1 (https://github.com/Puraav/bay-area-ev-gap-map)"
# Census of India 2011, district totals (latest official count):
# https://censusindia.gov.in/census.website/data/census-tables (Maharashtra, district A-1)
MUMBAI_POPULATION_2011 = {"Mumbai City": 3_085_411, "Mumbai Suburban": 9_356_962}
SF_COUNTY_GEOID = "0500000US06075"
ACS_POP_URL = (
    "https://www2.census.gov/programs-surveys/acs/summary_file/{year}/table-based-SF/"
    "data/5YRData/acsdt5y{year}-b01003.dat"
)
DC_SOCKETS = {"type1_combo", "type2_combo", "chademo", "tesla_supercharger", "gb_t_dc"}
DC_MIN_KW = 50
