"""Compute headline findings from processed data and save findings.json."""

import json

import pandas as pd

from evgap import config


def compute(z: pd.DataFrame, c: pd.DataFrame) -> dict:
    """Return the headline findings as a JSON-serialisable dict."""
    bay = c.set_index("county").loc["Bay Area total"]
    r = z[z["rankable"]]
    with_ports = r[~r["no_public_ports"]]
    zero = r[r["no_public_ports"]]

    top = r.sort_values("gap_rank").iloc[0]
    top_ported = with_ports.sort_values("evs_per_port", ascending=False).iloc[0]

    cs = c[c["county"] != "Bay Area total"].sort_values("evs_per_port")
    best, worst = cs.iloc[0], cs.iloc[-1]

    g75, s75 = r["ev_growth_2y"].quantile(0.75), r["gap_score"].quantile(0.75)
    hot = r[(r["ev_growth_2y"] >= g75) & (r["gap_score"] >= s75)]
    fastest = hot.sort_values("ev_growth_2y", ascending=False).iloc[0]

    def zip_info(row: pd.Series) -> dict:
        return {
            "zip": row["zip"],
            "city": row["city"],
            "county": row["county"],
            "evs": int(row["evs_2026"]),
            "public_ports": int(row["public_ports"]),
            "evs_per_port": None if row["no_public_ports"] else round(row["evs_per_port"], 1),
        }

    return {
        "bay_area": {
            "evs": int(bay["evs_2026"]),
            "bevs": int(bay["bevs_2026"]),
            "phevs": int(bay["phevs_2026"]),
            "public_ports": int(bay["public_ports"]),
            "l2_ports": int(bay["l2_ports"]),
            "dcfc_ports": int(bay["dcfc_ports"]),
            "evs_per_port": round(bay["evs_per_port"], 1),
            "ev_growth_2y": round(bay["ev_growth_2y"], 3),
        },
        "top_gap_zip": zip_info(top),
        "top_gap_zip_with_ports": {
            **zip_info(top_ported),
            "times_bay_area": round(top_ported["evs_per_port"] / bay["evs_per_port"], 1),
        },
        "counties": {
            "worst": {"county": worst["county"], "evs_per_port": round(worst["evs_per_port"], 1)},
            "best": {"county": best["county"], "evs_per_port": round(best["evs_per_port"], 1)},
            "ratio": round(worst["evs_per_port"] / best["evs_per_port"], 1),
        },
        "zero_port_zips": {
            "count": len(zero),
            "evs": int(zero["evs_2026"].sum()),
            "zips": zero.sort_values("evs_2026", ascending=False)["zip"].tolist(),
        },
        "fastest_growing_underserved": {
            **zip_info(fastest),
            "ev_growth_2y": round(fastest["ev_growth_2y"], 3),
            "gap_score": round(fastest["gap_score"], 1),
            "growth_threshold_p75": round(g75, 3),
            "gap_threshold_p75": round(s75, 1),
            "candidates": len(hot),
        },
        "dc_fast": {
            "bevs_per_dcfc": round(bay["bevs_per_dcfc"], 1),
            "tesla_share_of_dcfc": round(bay["tesla_dcfc_ports"] / bay["dcfc_ports"], 3),
        },
        "ranked_zips": len(r),
    }


def main() -> None:
    """Print the findings and save data/processed/findings.json."""
    z = pd.read_csv(config.PROCESSED_DIR / "zip_metrics.csv", dtype={"zip": str})
    c = pd.read_csv(config.PROCESSED_DIR / "county_metrics.csv")
    f = compute(z, c)
    (config.PROCESSED_DIR / "findings.json").write_text(json.dumps(f, indent=2))

    b, t, tp = f["bay_area"], f["top_gap_zip"], f["top_gap_zip_with_ports"]
    co, zp, fg, dc = (
        f["counties"],
        f["zero_port_zips"],
        f["fastest_growing_underserved"],
        f["dc_fast"],
    )
    print(
        f"1. The Bay Area has {b['evs']:,} EVs and {b['public_ports']:,} public charging ports "
        f"({b['l2_ports']:,} Level 2 + {b['dcfc_ports']:,} DC fast): "
        f"{b['evs_per_port']} EVs per public port."
    )
    print(
        f"2. Biggest gap: {t['zip']} ({t['city']}) has {t['evs']:,} EVs and zero public ports. "
        f"Among ZIPs with at least one port, {tp['zip']} ({tp['city']}) has {tp['evs']:,} EVs "
        f"sharing {tp['public_ports']} ports: {tp['evs_per_port']:,} EVs per port, "
        f"{tp['times_bay_area']}x the Bay Area average."
    )
    print(
        f"3. {co['worst']['county']} County has {co['worst']['evs_per_port']} EVs per public "
        f"port, {co['ratio']}x {co['best']['county']} ({co['best']['evs_per_port']})."
    )
    print(
        f"4. {zp['count']} of {f['ranked_zips']} ZIPs with 200+ EVs have zero public ports; "
        f"{zp['evs']:,} EVs are registered in them."
    )
    print(
        f"5. Fastest-growing under-served ZIP: {fg['zip']} ({fg['city']}), EVs up "
        f"{fg['ev_growth_2y'] * 100:.0f}% in two years, gap score {fg['gap_score']}/100 "
        f"({fg['evs']:,} EVs, {fg['public_ports']} public ports)."
    )
    print(
        f"6. DC fast: {dc['bevs_per_dcfc']} battery EVs per public DC fast port; "
        f"{dc['tesla_share_of_dcfc'] * 100:.0f}% of DC fast ports are Tesla."
    )


if __name__ == "__main__":
    main()
