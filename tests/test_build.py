"""Checks on the committed processed outputs and the core build helpers."""

import numpy as np
import pandas as pd
import pytest

from evgap import config
from evgap.build import assign_zcta_to_county, filter_ev_rows

COUNT_COLS = ["evs_2026", "bevs_2026", "l2_ports", "dcfc_ports"]


@pytest.fixture(scope="module")
def zips() -> pd.DataFrame:
    return pd.read_csv(config.PROCESSED_DIR / "zip_metrics.csv", dtype={"zip": str})


@pytest.fixture(scope="module")
def counties() -> pd.DataFrame:
    return pd.read_csv(config.PROCESSED_DIR / "county_metrics.csv")


def test_zip_column_is_unique_five_char_strings(zips):
    assert zips["zip"].map(lambda z: isinstance(z, str) and len(z) == 5 and z.isdigit()).all()
    assert not zips["zip"].duplicated().any()


def test_counties_are_bay_area(zips):
    assert set(zips["county"]) <= set(config.BAY_AREA_COUNTIES)


def test_row_count_in_range(zips):
    assert 150 <= len(zips) <= 300


def test_counts_are_non_negative_integers(zips):
    for col in COUNT_COLS:
        assert pd.api.types.is_integer_dtype(zips[col]), col
        assert (zips[col] >= 0).all(), col


def test_public_ports_is_l2_plus_dcfc(zips):
    assert (zips["public_ports"] == zips["l2_ports"] + zips["dcfc_ports"]).all()


def test_evs_per_port(zips):
    zero = zips["public_ports"] == 0
    assert zips.loc[zero, "evs_per_port"].isna().all()
    assert zips.loc[~zero, "evs_per_port"].notna().all()
    expected = zips.loc[~zero, "evs_2026"] / zips.loc[~zero, "public_ports"]
    np.testing.assert_allclose(zips.loc[~zero, "evs_per_port"], expected, atol=1e-6)


def test_rankable_and_gap_score(zips):
    r = zips["rankable"]
    assert (zips.loc[r, "evs_2026"] >= config.MIN_EVS_FOR_RANKING).all()
    assert (zips.loc[~r, "evs_2026"] < config.MIN_EVS_FOR_RANKING).all()
    assert zips.loc[r, "gap_score"].between(0, 100).all()
    assert zips.loc[~r, "gap_score"].isna().all()


def test_gap_rank_is_contiguous(zips):
    ranks = zips.loc[zips["rankable"], "gap_rank"].astype(int).sort_values()
    assert ranks.tolist() == list(range(1, len(ranks) + 1))
    assert zips.loc[~zips["rankable"], "gap_rank"].isna().all()


def test_county_totals_match_zip_sums(zips, counties):
    by_county = zips.groupby("county")[COUNT_COLS].sum()
    c = counties.set_index("county")
    for county, row in by_county.iterrows():
        for col in COUNT_COLS:
            assert c.loc[county, col] == row[col], (county, col)
    for col in COUNT_COLS:
        assert c.loc["Bay Area total", col] == zips[col].sum(), col


def test_renter_share_and_priority(zips):
    assert zips["renter_share"].dropna().between(0, 1).all()
    assert zips["renter_share"].notna().mean() > 0.9
    assert zips.loc[~zips["rankable"], "priority_score"].isna().all()
    assert zips["priority_score"].dropna().between(0, 100).all()


def test_assign_zcta_to_largest_land_overlap():
    rel = pd.DataFrame(
        {
            "zip": ["94000", "94000", "94001", "94002", "94002"],
            "county_fips": ["06001", "06013", "06075", "06081", "06085"],
            "land_part": [100, 900, 50, 500, 500],
        }
    )
    out = assign_zcta_to_county(rel).set_index("zip")["county_fips"]
    assert out.to_dict() == {
        "94000": "06013",
        "94001": "06075",
        "94002": "06081",
    }  # tie → lowest FIPS


def test_filter_ev_rows_keeps_light_duty_bev_phev_only():
    df = pd.DataFrame(
        {
            "zip_code": ["94110", "94110", "94110", "OOS", "9411", "94110"],
            "fuel": [
                "Battery Electric",
                "Plug-in Hybrid",
                "Gasoline",
                "Battery Electric",
                "Battery Electric",
                "Battery Electric",
            ],
            "duty": ["Light", "LIGHT", "Light", "Light", "Light", "Heavy"],
            "vehicles": ["5", "3", "40", "9", "9", "9"],
        }
    )
    out = filter_ev_rows(df)
    assert out["vehicles"].tolist() == ["5", "3"]
    assert set(out["fuel"]) <= config.EV_FUELS
