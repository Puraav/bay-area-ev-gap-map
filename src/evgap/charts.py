"""Export static PNG charts (LinkedIn / README) into charts/."""

import json
from datetime import datetime

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from evgap import config  # noqa: E402

ACCENT = "#eb6834"
GREY = "#c8c7c2"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#8a8984"
SIZE_IN, DPI = 8, 150  # 8 in × 150 dpi = 1200 px square
FOOTER = config.GITHUB_URL

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 11,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK_2,
        "xtick.color": INK_2,
        "ytick.color": INK_2,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


def load() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Load processed ZIP metrics, county metrics and build metadata."""
    z = pd.read_csv(config.PROCESSED_DIR / "zip_metrics.csv", dtype={"zip": str})
    c = pd.read_csv(config.PROCESSED_DIR / "county_metrics.csv")
    meta = json.loads((config.PROCESSED_DIR / "build_meta.json").read_text())
    return z, c, meta


def subtitle(meta: dict) -> str:
    """Data-source line built from the actual file dates."""
    dmv = datetime.strptime(meta["dmv_latest"].split()[0], "%m/%d/%Y").strftime("%b %Y")
    nrel = datetime.fromisoformat(meta["nrel_fetched_at"]).strftime("%b %Y")
    return f"Data: CA DMV ({dmv}), NREL AFDC ({nrel}). Public ports only."


def new_figure(title: str, sub: str) -> tuple[plt.Figure, plt.Axes]:
    """Square 1200 px figure with a finding-as-title, subtitle and footer."""
    fig = plt.figure(figsize=(SIZE_IN, SIZE_IN), dpi=DPI)
    fig.text(0.05, 0.955, title, fontsize=17, fontweight="bold", color=INK, va="top", wrap=True)
    fig.text(0.05, 0.875, sub, fontsize=10.5, color=INK_2, va="top")
    fig.text(0.05, 0.025, FOOTER, fontsize=9, color=MUTED)
    ax = fig.add_axes((0.30, 0.09, 0.62, 0.75))
    return fig, ax


def clean_axes(ax: plt.Axes, keep_left: bool = False) -> None:
    """Remove chart junk: spines, ticks and gridlines."""
    for side in ["top", "right", "bottom"] + ([] if keep_left else ["left"]):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)
    ax.grid(False)


def save(fig: plt.Figure, name: str) -> str:
    """Save a figure into charts/ and return its path."""
    config.CHARTS_DIR.mkdir(exist_ok=True)
    path = config.CHARTS_DIR / name
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return str(path)


def hbar(
    ax: plt.Axes,
    labels: list[str],
    values: list[float],
    accent: list[bool],
    fmt: str = "{:,.0f}",
    inside: bool = False,
) -> None:
    """Horizontal bars, largest on top, grey with accent bars and value labels."""
    y = range(len(values))[::-1]
    colors = [ACCENT if a else GREY for a in accent]
    ax.barh(list(y), values, color=colors, height=0.72, edgecolor="white", linewidth=1)
    ax.set_yticks(list(y), labels, fontsize=10.5, color=INK)
    ax.set_xticks([])
    pad = max(values) * 0.012
    for yi, v, a in zip(y, values, accent, strict=True):
        if inside:  # label at the inner end of the bar, clear of reference lines
            ax.text(
                v - pad,
                yi,
                fmt.format(v),
                va="center",
                ha="right",
                fontsize=10.5,
                color=INK,
                fontweight="bold" if a else "normal",
                zorder=4,
            )
            continue
        ax.text(
            v + pad,
            yi,
            fmt.format(v),
            va="center",
            fontsize=10,
            zorder=4,
            color=INK if a else INK_2,
            fontweight="bold" if a else "normal",
            bbox={"boxstyle": "square,pad=0.15", "fc": "white", "ec": "none"},
        )
    ax.set_xlim(0, max(values) * 1.12)
    clean_axes(ax, keep_left=False)


def chart_top_zips(z: pd.DataFrame, c: pd.DataFrame, meta: dict) -> str:
    """01: top 15 rankable ZIPs (with ≥1 port) by EVs per public port."""
    top = z[z["rankable"] & ~z["no_public_ports"]].nlargest(15, "evs_per_port")
    bay = c.set_index("county").loc["Bay Area total", "evs_per_port"]
    first = top.iloc[0]
    title = (
        f"{first['city']} ZIP {first['zip']} has {first['evs_per_port']:,.0f} EVs\n"
        f"per public charging port — {first['evs_per_port'] / bay:.0f}× the Bay Area average"
    )
    n_zero = int((z["rankable"] & z["no_public_ports"]).sum())
    sub = (
        subtitle(meta) + f"\nTop 15 ZIPs with ≥ {config.MIN_EVS_FOR_RANKING} EVs and at least "
        f"one public port. {n_zero} more ZIPs have none at all. Bay Area: {bay:.1f}."
    )
    fig, ax = new_figure(title, sub)
    labels = [f"{r.zip} · {r.city}" for r in top.itertuples()]
    hbar(ax, labels, top["evs_per_port"].tolist(), [i == 0 for i in range(len(top))])
    return save(fig, "01_top_gap_zips.png")


def chart_counties(c: pd.DataFrame, meta: dict) -> str:
    """02: EVs per public port by county with a Bay Area average line."""
    bay = c.set_index("county").loc["Bay Area total", "evs_per_port"]
    cs = c[c["county"] != "Bay Area total"].sort_values("evs_per_port", ascending=False)
    worst, best = cs.iloc[0], cs.iloc[-1]
    title = (
        f"{worst['county']} County has {worst['evs_per_port']:.0f} EVs per public port,\n"
        f"{worst['evs_per_port'] / best['evs_per_port']:.1f}× {best['county']}'s "
        f"{best['evs_per_port']:.0f}"
    )
    fig, ax = new_figure(title, subtitle(meta) + "\nDashed line: Bay Area average.")
    hbar(
        ax,
        cs["county"].tolist(),
        cs["evs_per_port"].tolist(),
        [i == 0 for i in range(len(cs))],
        fmt="{:.1f}",
        inside=True,
    )
    ax.axvline(bay, color=INK_2, linestyle=(0, (4, 3)), linewidth=1, zorder=0.5)
    ax.text(bay, len(cs) - 0.35, f" Bay Area {bay:.1f}", color=INK_2, fontsize=9.5, va="bottom")
    return save(fig, "02_county_comparison.png")


def chart_map(z: pd.DataFrame, meta: dict) -> str:
    """03: static choropleth of gap_score with county borders and top-5 labels."""
    shapes = gpd.read_file(config.PROCESSED_DIR / "bay_area_zcta.geojson")
    g = shapes.merge(z, on="zip").to_crs(3310)  # California Albers (metres)
    counties = g.dissolve(by="county")
    zero = z[z["rankable"] & z["no_public_ports"]]
    title = (
        f"{len(zero)} Bay Area ZIP codes with 200+ EVs have\n"
        f"zero public chargers — {zero['evs_2026'].sum():,} EVs between them"
    )
    fig = plt.figure(figsize=(SIZE_IN, SIZE_IN), dpi=DPI)
    fig.text(0.05, 0.955, title, fontsize=17, fontweight="bold", color=INK, va="top")
    fig.text(
        0.05,
        0.875,
        subtitle(meta) + "\nGap score: percentile of EVs per public port "
        "(darker = bigger gap). Grey: < 200 EVs, not ranked.",
        fontsize=10.5,
        color=INK_2,
        va="top",
    )
    fig.text(0.05, 0.025, FOOTER, fontsize=9, color=MUTED)
    ax = fig.add_axes((0.02, 0.06, 0.96, 0.78))
    g[g["gap_score"].isna()].plot(ax=ax, color="#ecebe7", edgecolor="white", linewidth=0.2)
    g[g["gap_score"].notna()].plot(
        ax=ax,
        column="gap_score",
        cmap="Oranges",
        vmin=0,
        vmax=100,
        edgecolor="white",
        linewidth=0.2,
    )
    counties.boundary.plot(ax=ax, color=INK_2, linewidth=0.6)
    ax.set_axis_off()
    label_top5(ax, g)
    sm = plt.cm.ScalarMappable(cmap="Oranges", norm=plt.Normalize(0, 100))
    cax = fig.add_axes((0.70, 0.80, 0.25, 0.012))
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cb.set_ticks([0, 50, 100], labels=["0 small gap", "50", "100 big gap"], fontsize=8.5)
    cb.outline.set_visible(False)
    return save(fig, "03_gap_map.png")


def label_top5(ax: plt.Axes, g: gpd.GeoDataFrame) -> None:
    """Label the 5 biggest-gap ZIPs in two margin columns (west / east) with leader lines."""
    top5 = g[g["gap_rank"].notna()].nsmallest(5, "gap_rank").copy()
    pts = top5.geometry.representative_point()
    top5["px"], top5["py"] = pts.x, pts.y
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    mid_x = top5["px"].median()
    for west, side in [(True, top5[top5["px"] <= mid_x]), (False, top5[top5["px"] > mid_x])]:
        side = side.sort_values("py", ascending=False)
        n = len(side)
        cy = side["py"].mean()
        step = (y1 - y0) * 0.055
        for i, r in enumerate(side.itertuples()):
            ty = cy + (n - 1) / 2 * step - i * step
            tx = x0 + (x1 - x0) * (0.06 if west else 0.80)
            ax.annotate(
                f"#{int(r.gap_rank)} {r.zip} {r.city}",
                (r.px, r.py),
                xytext=(tx, ty),
                fontsize=9.5,
                color=INK,
                ha="right" if west else "left",
                va="center",
                arrowprops={"arrowstyle": "-", "color": INK, "lw": 0.7, "shrinkA": 2, "shrinkB": 0},
                bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "none"},
            )
        ax.scatter(side["px"], side["py"], s=10, color=INK, zorder=5)


def chart_growth(z: pd.DataFrame, meta: dict) -> str:
    """04: 2-year EV growth vs EVs per port; top-right = fast-growing and under-served."""
    d = z[z["rankable"] & ~z["no_public_ports"]].copy()
    gx, gy = d["ev_growth_2y"].median(), d["evs_per_port"].median()
    tr = d[(d["ev_growth_2y"] > gx) & (d["evs_per_port"] > gy)]
    title = (
        f"{len(tr)} of {len(d)} ranked ZIPs are both fast-growing\n"
        f"and under-served (EV growth > {gx * 100:.0f}%, > {gy:.0f} EVs per port)"
    )
    sub = (
        subtitle(meta) + "\nLines at the medians. Dot size = EVs. "
        "ZIPs with zero public ports are not shown (no ratio)."
    )
    fig, ax = new_figure(title, sub)
    ax.set_position((0.11, 0.12, 0.84, 0.70))
    in_tr = d.index.isin(tr.index)
    sizes = d["evs_2026"] / d["evs_2026"].max() * 400 + 8
    xmax = 125.0
    gx_pct = (d["ev_growth_2y"] * 100).clip(upper=xmax)
    ax.scatter(
        gx_pct,
        d["evs_per_port"],
        s=sizes,
        c=[ACCENT if t else GREY for t in in_tr],
        edgecolors="white",
        linewidths=0.8,
        alpha=0.9,
    )
    ax.set_yscale("log")
    ax.set_xlim((d["ev_growth_2y"].min() * 100) - 10, xmax + 8)
    for r in d[d["ev_growth_2y"] * 100 > xmax].itertuples():
        ax.annotate(
            f"{r.zip} {r.city}: +{r.ev_growth_2y * 100:,.0f}%\n(off scale; likely "
            "fleet registrations)",
            (xmax, r.evs_per_port),
            xytext=(-8, -4),
            textcoords="offset points",
            ha="right",
            va="top",
            fontsize=8.5,
            color=INK_2,
        )
    ax.axvline(gx * 100, color=MUTED, linestyle=(0, (4, 3)), linewidth=0.8)
    ax.axhline(gy, color=MUTED, linestyle=(0, (4, 3)), linewidth=0.8)
    ax.set_xlabel("EV growth, Jan 2024 to Jan 2026 (%)")
    ax.set_ylabel("EVs per public port (log scale)")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    # Label the 5 most extreme: furthest into the top-right by combined rank.
    d["_ext"] = d["ev_growth_2y"].rank(pct=True) + d["evs_per_port"].rank(pct=True)
    ext = d.nlargest(5, "_ext").sort_values("evs_per_port", ascending=False)
    for i, r in enumerate(ext.itertuples()):
        ty = 900 / (1.55**i)  # evenly spaced on the log axis, upper right
        ax.annotate(
            f"{r.zip} {r.city} (+{r.ev_growth_2y * 100:.0f}%, {r.evs_per_port:,.0f})",
            (r.ev_growth_2y * 100, r.evs_per_port),
            xytext=(88, ty),
            fontsize=9,
            color=INK,
            va="center",
            arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.6, "shrinkB": 3},
        )
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    return save(fig, "04_growth_vs_ports.png")


def load_city() -> dict | None:
    """SF vs Mumbai comparison (python -m evgap.mumbai), if it has been built."""
    path = config.PROCESSED_DIR / "city_comparison.json"
    return json.loads(path.read_text()) if path.exists() else None


def city_subtitle(cc: dict) -> str:
    """Source line for the SF vs Mumbai charts."""
    osm = datetime.fromisoformat(cc["osm_fetched_at"]).strftime("%b %Y")
    return f"Data: CA DMV, NREL AFDC, Vahan ({len(cc['Mumbai']['rtos'])} Mumbai RTOs), OpenStreetMap. {osm}."


def chart_data_access(cc: dict) -> str:
    """05: scorecard of what public data exists for SF vs Mumbai."""
    s, m, d = cc["San Francisco"], cc["Mumbai"], cc["data_access"]
    title = (
        f"One Mumbai EV data area covers {d['resolution_ratio']}× more\n"
        "people than one San Francisco ZIP code"
    )
    rows = [
        (
            "EV counts published for",
            f"{d['sf_geo_units']} ZIP codes",
            f"{d['mumbai_geo_units']} RTOs",
        ),
        ("People per area", f"{d['sf_people_per_unit']:,}", f"{d['mumbai_people_per_unit']:,}"),
        ("Getting the EV counts", "Open CSV + API", "Manual Excel export\nper RTO"),
        (
            "Official public\ncharger list",
            f"Yes (NREL API)\n{d['sf_official_charger_stations']:,} stations",
            "None found",
        ),
        (
            "Chargers in\nOpenStreetMap",
            f"{s['osm_stations']:,} stations",
            f"{m['osm_stations']:,} stations",
        ),
        (
            "Latest official\npopulation count",
            s["population_year"].replace("ACS ", "ACS\n"),
            f"Census {m['population_year']}",
        ),
    ]
    fig = plt.figure(figsize=(SIZE_IN, SIZE_IN), dpi=DPI)
    fig.text(0.05, 0.955, title, fontsize=17, fontweight="bold", color=INK, va="top")
    fig.text(
        0.05,
        0.875,
        city_subtitle(cc) + "\nWhat anyone can find out, from public sources, "
        "about EVs and chargers in each city.",
        fontsize=10,
        color=INK_2,
        va="top",
    )
    fig.text(0.05, 0.025, FOOTER, fontsize=9, color=MUTED)
    x_label, x_sf, x_mum = 0.05, 0.42, 0.72
    top, step = 0.74, 0.105
    fig.text(
        x_sf, top + 0.045, "San Francisco", fontsize=13, fontweight="bold", color=INK_2, va="center"
    )
    fig.text(
        x_mum, top + 0.045, "Mumbai", fontsize=13, fontweight="bold", color=ACCENT, va="center"
    )
    for i, (label, a, b) in enumerate(rows):
        y = top - i * step
        fig.add_artist(plt.Line2D([0.05, 0.95], [y - step / 2] * 2, color="#e6e5e0", lw=1))
        fig.text(x_label, y, label, fontsize=11.5, color=INK_2, va="center")
        fig.text(x_sf, y, a, fontsize=12.5, color=INK, va="center")
        fig.text(x_mum, y, b, fontsize=12.5, color=INK, va="center", fontweight="bold")
    return save(fig, "05_sf_vs_mumbai_data.png")


def chart_mumbai_mix(cc: dict) -> str:
    """06: Mumbai's EVs by vehicle type (two-wheelers vs cars)."""
    m = cc["Mumbai"]
    mix = [
        ("Two-wheelers", m["ev_two_wheelers"]),
        ("Cars + cabs", m["ev_cars"]),
        ("Other (buses, goods)", m["ev_other"]),
        ("Three-wheelers", m["ev_three_wheelers"]),
    ]
    total = sum(v for _, v in mix)
    title = (
        f"Mumbai has more electric two-wheelers ({m['ev_two_wheelers']:,})\n"
        f"than electric cars ({m['ev_cars']:,})"
    )
    sub = (
        city_subtitle(cc) + f"\nAll {total:,} EVs ever registered at Mumbai's 4 RTOs, by type. "
        f"EVs are {m['ev_share_of_cars']:.1%} of registered cars (SF: "
        f"{cc['San Francisco']['ev_share_of_cars']:.1%})."
    )
    fig, ax = new_figure(title, sub)
    ax.set_position((0.30, 0.10, 0.62, 0.70))
    hbar(ax, [k for k, _ in mix], [v for _, v in mix], [i == 0 for i in range(len(mix))])
    return save(fig, "06_mumbai_ev_mix.png")


def main() -> None:
    """Export all charts and print a one-line description of each."""
    z, c, meta = load()
    paths = [
        chart_top_zips(z, c, meta),
        chart_counties(c, meta),
        chart_map(z, meta),
        chart_growth(z, meta),
    ]
    cc = load_city()
    if cc:
        paths += [chart_data_access(cc), chart_mumbai_mix(cc)]
    for p in paths:
        size = config.CHARTS_DIR.joinpath(p.split("/")[-1]).stat().st_size / 1e6
        print(f"{p.split('/')[-1]}  ({size:.2f} MB)")


if __name__ == "__main__":
    main()
