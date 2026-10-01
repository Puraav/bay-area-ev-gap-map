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
