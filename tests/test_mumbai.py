"""Checks on the SF vs Mumbai comparison and its parsers."""

import json

import pandas as pd
import pytest

from evgap import config
from evgap.mumbai import station_ports, to_int

CITY_JSON = config.PROCESSED_DIR / "city_comparison.json"


def test_to_int_handles_indian_grouping():
    assert to_int("7,47,831") == 747831
    assert to_int("0") == 0
    assert to_int(None) == 0


def test_station_ports_capacity_sockets_and_dc():
    assert station_ports({"capacity": "4"}) == (4, False)
    assert station_ports({"socket:type2": "2", "socket:type2_combo": "1"}) == (3, True)
    assert station_ports({"socket:nacs": "2", "socket:nacs:output": "250 kW"}) == (2, True)
    assert station_ports({"socket:nacs": "2", "socket:nacs:output": "11 kW"}) == (2, False)
    assert station_ports({}) == (1, False)


@pytest.mark.skipif(not CITY_JSON.exists(), reason="run python -m evgap.mumbai first")
def test_city_comparison_matches_sf_county():
    c = json.loads(CITY_JSON.read_text())
    sf = pd.read_csv(config.PROCESSED_DIR / "county_metrics.csv").set_index("county")
    sf = sf.loc["San Francisco"]
    assert c["San Francisco"]["ev_cars"] == sf["evs_2026"]
    assert c["San Francisco"]["nrel_ports"] == sf["public_ports"]
    assert sorted(c["Mumbai"]["rtos"]) == sorted(config.MUMBAI_RTOS)
    for city in ["San Francisco", "Mumbai"]:
        for k, v in c[city].items():
            if isinstance(v, int | float):
                assert v >= 0, (city, k)
