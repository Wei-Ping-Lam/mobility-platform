"""
Shared constants, data loaders, and scoring helpers for the FIFA 2026
Mobility Readiness Platform. Every tab module imports from here — this
is the one file that touches raw data and defines cross-tab constants.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import glob
import json
from pathlib import Path

DATA_ROOT = Path(__file__).parent.parent
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

PLOTLY_TEMPLATE = "plotly_dark"
MAP_STYLE = "carto-darkmatter"

# ── Default readiness-score weights ─────────────────────────────────────────
# (previously sidebar sliders; now fixed defaults adjustable via the
#  "Adjust Readiness Score Weights" expander in app.py)
DEFAULT_WEIGHTS = {
    "transit": 0.35,
    "heat": 0.20,
    "uhi": 0.15,
    "access": 0.30,
}

# ── Constants ────────────────────────────────────────────────────────────────

HOST_CITIES = {
    "Atlanta": {
        "state": "GA", "market_key": "Atlanta",
        "lat": 33.749, "lon": -84.388,
        "venue": "Mercedes-Benz Stadium", "capacity": 71000, "games": 6,
        "transit_score": 68, "accessibility_score": 72,
        "transit_mode": "MARTA Rail",
    },
    "Boston": {
        "state": "MA", "market_key": "Boston",
        "lat": 42.361, "lon": -71.057,
        "venue": "Gillette Stadium", "capacity": 65878, "games": 5,
        "transit_score": 88, "accessibility_score": 55,
        "transit_mode": "MBTA Commuter Rail",
    },
    "Dallas": {
        "state": "TX", "market_key": "Dallas",
        "lat": 32.748, "lon": -97.093,
        "venue": "AT&T Stadium", "capacity": 80000, "games": 9,
        "transit_score": 42, "accessibility_score": 55,
        "transit_mode": "DART Light Rail",
    },
    "Houston": {
        "state": "TX", "market_key": "Houston",
        "lat": 29.761, "lon": -95.362,
        "venue": "NRG Stadium", "capacity": 72220, "games": 5,
        "transit_score": 38, "accessibility_score": 60,
        "transit_mode": "METRORail",
    },
    "Kansas City": {
        "state": "MO", "market_key": "Kansas City",
        "lat": 39.049, "lon": -94.484,
        "venue": "Arrowhead Stadium", "capacity": 76416, "games": 6,
        "transit_score": 35, "accessibility_score": 58,
        "transit_mode": "Limited Bus / Shuttle",
    },
    "Los Angeles": {
        "state": "CA", "market_key": "Los Angeles",
        "lat": 33.953, "lon": -118.338,
        "venue": "SoFi Stadium", "capacity": 70240, "games": 8,
        "transit_score": 65, "accessibility_score": 60,
        "transit_mode": "Metro C Line",
    },
    "Miami": {
        "state": "FL", "market_key": "Miami",
        "lat": 25.958, "lon": -80.239,
        "venue": "Hard Rock Stadium", "capacity": 65326, "games": 8,
        "transit_score": 55, "accessibility_score": 50,
        "transit_mode": "Metrorail + Shuttle",
    },
    "New York/NJ": {
        "state": "NJ", "market_key": "New York",
        "lat": 40.814, "lon": -74.075,
        "venue": "MetLife Stadium", "capacity": 82500, "games": 8,
        "transit_score": 95, "accessibility_score": 70,
        "transit_mode": "NJ Transit / Meadowlands",
    },
    "Philadelphia": {
        "state": "PA", "market_key": "Philadelphia",
        "lat": 39.901, "lon": -75.167,
        "venue": "Lincoln Financial Field", "capacity": 69796, "games": 6,
        "transit_score": 82, "accessibility_score": 75,
        "transit_mode": "SEPTA Broad Street Line",
    },
    "San Francisco": {
        "state": "CA", "market_key": "SF Bay",
        "lat": 37.403, "lon": -121.970,
        "venue": "Levi's Stadium", "capacity": 68500, "games": 7,
        "transit_score": 85, "accessibility_score": 80,
        "transit_mode": "VTA / Caltrain",
    },
    "Seattle": {
        "state": "WA", "market_key": "Seattle",
        "lat": 47.595, "lon": -122.332,
        "venue": "Lumen Field", "capacity": 72000, "games": 6,
        "transit_score": 75, "accessibility_score": 85,
        "transit_mode": "Sound Transit Link",
    },
}

SUMMER_CLIMATE = {
    "Atlanta":       {"avg_temp_c": 28.3, "max_temp_c": 33.1, "humidity": 68},
    "Boston":        {"avg_temp_c": 22.1, "max_temp_c": 27.3, "humidity": 65},
    "Dallas":        {"avg_temp_c": 33.5, "max_temp_c": 39.2, "humidity": 52},
    "Houston":       {"avg_temp_c": 31.7, "max_temp_c": 36.5, "humidity": 75},
    "Kansas City":   {"avg_temp_c": 27.9, "max_temp_c": 33.0, "humidity": 63},
    "Los Angeles":   {"avg_temp_c": 24.1, "max_temp_c": 28.5, "humidity": 72},
    "Miami":         {"avg_temp_c": 29.8, "max_temp_c": 33.3, "humidity": 82},
    "New York/NJ":   {"avg_temp_c": 25.6, "max_temp_c": 29.6, "humidity": 64},
    "Philadelphia":  {"avg_temp_c": 26.8, "max_temp_c": 31.2, "humidity": 66},
    "San Francisco": {"avg_temp_c": 17.2, "max_temp_c": 20.1, "humidity": 78},
    "Seattle":       {"avg_temp_c": 18.9, "max_temp_c": 23.4, "humidity": 62},
}

# Match schedule (approximate; final draw TBD)
MATCH_SCHEDULE = {
    # group = group stage matches; knockout = R32 + R16 + QF + SF + Final/3rd
    # US total: 78 of 104 tournament matches  (Canada: 13, Mexico: 13)
    "Dallas":        {"group": 5, "knockout": 4, "round": "SF"},    # 9 total
    "Atlanta":       {"group": 5, "knockout": 3, "round": "SF"},    # 8 total
    "Los Angeles":   {"group": 5, "knockout": 3, "round": "QF"},    # 8 total
    "New York/NJ":   {"group": 5, "knockout": 3, "round": "Final"}, # 8 total
    "Boston":        {"group": 5, "knockout": 2, "round": "QF"},    # 7 total
    "Houston":       {"group": 5, "knockout": 2, "round": "R16"},   # 7 total
    "Miami":         {"group": 4, "knockout": 3, "round": "QF"},    # 7 total (incl. 3rd place)
    "Kansas City":   {"group": 4, "knockout": 2, "round": "QF"},    # 6 total
    "Philadelphia":  {"group": 5, "knockout": 1, "round": "R16"},   # 6 total
    "San Francisco": {"group": 5, "knockout": 1, "round": "R32"},   # 6 total
    "Seattle":       {"group": 4, "knockout": 2, "round": "R16"},   # 6 total
}

# ── Category-level FIFA demand multipliers ───────────────────────────────────
# Benchmarks drawn from:
#   [A] US Travel Association (2019) "The Economic Impact of Mega-Sporting Events"
#   [B] Baade & Matheson, Journal of Sports Economics 17(1), 2016
#   [C] FIFA 2022 LOC Official Economic Impact Assessment
#   [D] FIFA 2018 Official Economic Impact Assessment
# Format: category_name → (benchmark_multiplier, citation)
CATEGORY_FIFA_BENCHMARKS = {
    "Restaurants and Other Eating Places":           (4.1, "[A]"),
    "Amusement Parks and Arcades":                   (5.2, "[B]"),
    "Spectator Sports":                              (5.5, "[B]"),
    "Other Amusement and Recreation Industries":     (4.8, "[B]"),
    "Travel Arrangement and Reservation Services":   (3.5, "[C]"),
    "Investigation and Security Services":           (1.8, "[C]"),
    "Personal Care Services":                        (1.5, "[D]"),
    "Health and Personal Care Stores":               (1.2, "[D]"),
    "Automotive Repair and Maintenance":             (1.0, "[D]"),
    "Personal and Household Goods Repair and Maintenance": (1.0, "[D]"),
    "Electronic and Precision Equipment Repair and Maintenance": (1.0, "[D]"),
    "Offices of Dentists":                           (0.9, "Baseline"),
    "Offices of Other Health Practitioners":         (0.9, "Baseline"),
    "Other Schools and Instruction":                 (0.9, "Baseline"),
    "Business Schools and Computer and Management Training": (0.9, "Baseline"),
    "Technical and Trade Schools":                   (0.9, "Baseline"),
    "Employment Services":                           (1.0, "Baseline"),
    "Business Support Services":                     (1.0, "Baseline"),
    "Services to Buildings and Dwellings":           (1.0, "Baseline"),
    "Management of Companies and Enterprises":       (1.0, "Baseline"),
    "Lessors of Real Estate":                        (1.0, "Baseline"),
    "Other Investment Pools and Funds":              (1.0, "Baseline"),
    "Agencies":                                      (1.0, "Baseline"),
    "Other Professional":                            (1.0, "Baseline"),
    "Other Support Services":                        (1.0, "Baseline"),
    "Waste Collection":                              (1.0, "Baseline"),
    "Waste Treatment and Disposal":                  (1.0, "Baseline"),
}
_DEFAULT_BENCHMARK = (1.3, "Baseline")

# Categories worth displaying in the FIFA surge chart (multiplier > 1.2)
FIFA_RELEVANT_CATEGORIES = {k for k, (v, _) in CATEGORY_FIFA_BENCHMARKS.items() if v > 1.2}


def get_category_benchmark(category_name):
    return CATEGORY_FIFA_BENCHMARKS.get(category_name, _DEFAULT_BENCHMARK)


# ── Data loaders ─────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Loading store visit patterns…")
def load_store_visits():
    cache = CACHE_DIR / "store_visits_agg.parquet"
    if cache.exists():
        return pd.read_parquet(cache)

    files = sorted(glob.glob(str(DATA_ROOT / "store-visits-rice" / "*.gz")))[:2]
    chunks = []
    for f in files:
        try:
            df = pd.read_csv(
                f,
                usecols=["MARKET", "LOCAL_DATE", "DAILY_VISITS", "CATEGORY"],
                nrows=250_000,
            )
            chunks.append(df)
        except Exception:
            continue

    if not chunks:
        return pd.DataFrame(columns=["market", "date", "daily_visits"])

    combined = pd.concat(chunks, ignore_index=True)
    combined["LOCAL_DATE"] = pd.to_datetime(combined["LOCAL_DATE"])
    agg = (
        combined.groupby(["MARKET", "LOCAL_DATE"])["DAILY_VISITS"]
        .sum()
        .reset_index()
        .rename(columns={"MARKET": "market", "LOCAL_DATE": "date", "DAILY_VISITS": "daily_visits"})
    )
    agg.to_parquet(cache)
    return agg


@st.cache_data(show_spinner="Loading category-level visit patterns…")
def load_store_visits_by_category():
    """
    Aggregate store-visits by MARKET × date × CATEGORY.
    Reads more partitions than the totals loader to capture category diversity.
    """
    cache = CACHE_DIR / "store_visits_cat_agg.parquet"
    if cache.exists():
        return pd.read_parquet(cache)

    # Sample broadly across all 32 partitions (fewer rows each) for category coverage
    files = sorted(glob.glob(str(DATA_ROOT / "store-visits-rice" / "*.gz")))
    chunks = []
    step = max(1, len(files) // 8)          # read every 4th file → up to 8 files
    for f in files[::step]:
        try:
            df = pd.read_csv(
                f,
                usecols=["MARKET", "LOCAL_DATE", "DAILY_VISITS", "CATEGORY"],
                nrows=50_000,
            )
            chunks.append(df)
        except Exception:
            continue

    if not chunks:
        return pd.DataFrame(columns=["market", "date", "category", "daily_visits"])

    combined = pd.concat(chunks, ignore_index=True)
    combined["LOCAL_DATE"] = pd.to_datetime(combined["LOCAL_DATE"])
    combined["CATEGORY"] = combined["CATEGORY"].fillna("Other")
    agg = (
        combined.groupby(["MARKET", "LOCAL_DATE", "CATEGORY"])["DAILY_VISITS"]
        .sum()
        .reset_index()
        .rename(columns={
            "MARKET": "market", "LOCAL_DATE": "date",
            "CATEGORY": "category", "DAILY_VISITS": "daily_visits",
        })
    )
    agg.to_parquet(cache)
    return agg


def compute_category_surge(visits_cat_df, market_key):
    """
    For each category in this market, blend the published FIFA benchmark with
    the data-derived historical variability (p90 / median).
    Returns a DataFrame sorted by projected multiplier descending.
    """
    if visits_cat_df.empty:
        return pd.DataFrame()

    mkt = visits_cat_df[
        visits_cat_df["market"].str.contains(market_key, case=False, na=False)
    ]
    if mkt.empty:
        return pd.DataFrame()

    rows = []
    for cat, grp in mkt.groupby("category"):
        visits = grp["daily_visits"].dropna()
        if len(visits) < 10:
            continue
        median_v = float(visits.median())
        p90_v    = float(np.percentile(visits, 90))
        hist_var = (p90_v / median_v) if median_v > 0 else 1.0

        benchmark, citation = get_category_benchmark(cat)

        # Adjust benchmark upward for categories that already show high local volatility
        # (a market where entertainment already spikes 3× may see even higher WC surge)
        adjusted = round(benchmark * (1 + 0.2 * max(0, hist_var - 1)), 2)

        rows.append({
            "Category":              cat,
            "Baseline Visits/Day":   round(median_v),
            "Hist. Variability":     round(hist_var, 2),
            "FIFA Benchmark":        benchmark,
            "Projected Multiplier":  adjusted,
            "Source":                citation,
            "Projected Visits/Day":  round(median_v * adjusted),
        })

    return (
        pd.DataFrame(rows)
        .sort_values("Projected Multiplier", ascending=False)
        .reset_index(drop=True)
    )


@st.cache_data(show_spinner="Loading urban heat index…")
def load_uhi():
    cache = CACHE_DIR / "uhi_summary.parquet"
    if cache.exists():
        return pd.read_parquet(cache)

    files = glob.glob(str(DATA_ROOT / "urban-heat-index-rice" / "*.gz"))
    dfs = []
    for f in files:
        try:
            dfs.append(pd.read_csv(f))
        except Exception:
            continue

    if not dfs:
        return pd.DataFrame(columns=["MARKET", "avg_uhi", "max_uhi", "p90_uhi"])

    combined = pd.concat(dfs, ignore_index=True)
    summary = combined.groupby("MARKET").agg(
        avg_uhi=("UHI", "mean"),
        max_uhi=("UHI", "max"),
        p90_uhi=("UHI", lambda x: np.percentile(x, 90)),
    ).reset_index()
    summary.to_parquet(cache)
    return summary


@st.cache_data(show_spinner="Loading GTFS transit scores…")
def load_gtfs_scores():
    """Load pre-computed GTFS stop-density scores from fetch_gtfs.py output."""
    for path in [
        CACHE_DIR / "gtfs_transit_scores.json",
        Path(__file__).parent.parent / "data" / "gtfs_transit_scores.json",
    ]:
        if path.exists():
            return json.loads(path.read_text())
    return {}


@st.cache_data(show_spinner="Analyzing visitor origin patterns…")
def load_spend_origins():
    """Parse CUSTOMER_HOME_CITY JSON from spend-patterns to map fan origin corridors."""
    cache = CACHE_DIR / "spend_origins.parquet"
    if cache.exists():
        return pd.read_parquet(cache)

    files = sorted(glob.glob(str(DATA_ROOT / "spend-patterns-rice" / "*.gz")))[:1]
    if not files:
        return pd.DataFrame(columns=["market", "home_state", "count"])

    try:
        df = pd.read_csv(
            files[0],
            usecols=["MARKET", "CUSTOMER_HOME_CITY"],
            nrows=3000,
        ).dropna(subset=["CUSTOMER_HOME_CITY"])
    except Exception:
        return pd.DataFrame(columns=["market", "home_state", "count"])

    records = []
    for mkt, raw in zip(df["MARKET"], df["CUSTOMER_HOME_CITY"]):
        try:
            for city_state, cnt in json.loads(raw).items():
                state = city_state.rsplit(", ", 1)[-1] if ", " in city_state else "Unknown"
                records.append({"market": mkt, "home_state": state, "count": int(cnt)})
        except Exception:
            continue

    if not records:
        return pd.DataFrame(columns=["market", "home_state", "count"])

    out = (
        pd.DataFrame(records)
        .groupby(["market", "home_state"])["count"]
        .sum()
        .reset_index()
    )
    out.to_parquet(cache)
    return out


@st.cache_data(show_spinner="Computing city metrics…")
def build_city_metrics(visits_hash: str, uhi_hash: str):
    """Build per-city mobility readiness metrics. Hash params bust cache on data reload."""
    visits_df   = load_store_visits()
    uhi_df      = load_uhi()
    gtfs_scores = load_gtfs_scores()

    rows = []
    for city, meta in HOST_CITIES.items():
        climate = SUMMER_CLIMATE[city]
        # GTFS-derived score where available; fall back to expert estimate
        gtfs = gtfs_scores.get(city, {})
        gtfs_score = gtfs.get("gtfs_transit_score", 0)
        if gtfs_score > 5:
            transit_score  = gtfs_score
            transit_source = "GTFS"
        else:
            transit_score  = meta["transit_score"]
            transit_source = "estimated"
        access_score = meta["accessibility_score"]
        mk = meta["market_key"]

        # UHI lookup
        uhi_match = (
            uhi_df[uhi_df["MARKET"].str.contains(mk, case=False, na=False)]
            if not uhi_df.empty else pd.DataFrame()
        )
        avg_uhi = float(uhi_match["avg_uhi"].values[0]) if not uhi_match.empty else 5.0
        p90_uhi = float(uhi_match["p90_uhi"].values[0]) if not uhi_match.empty else 8.0

        # Visit baseline
        v_match = (
            visits_df[visits_df["market"].str.contains(mk, case=False, na=False)]
            if not visits_df.empty else pd.DataFrame()
        )
        avg_visits = float(v_match["daily_visits"].mean()) if not v_match.empty else 0.0
        peak_visits = float(v_match["daily_visits"].max()) if not v_match.empty else 0.0

        # Heat stress index
        temp = climate["avg_temp_c"]
        hum = climate["humidity"]
        heat_idx = temp + 0.5 * max(0, hum - 40) * (temp / 30)
        heat_score = max(0.0, min(100.0, 100 - (heat_idx - 20) * 2.2))

        # UHI score (lower UHI = better walkability)
        uhi_score = max(0.0, min(100.0, 100 - avg_uhi * 7))

        # Composite mobility readiness (0–100) — recomputed with user weights in app.py
        composite = (
            transit_score * DEFAULT_WEIGHTS["transit"]
            + heat_score * DEFAULT_WEIGHTS["heat"]
            + uhi_score * DEFAULT_WEIGHTS["uhi"]
            + access_score * DEFAULT_WEIGHTS["access"]
        )

        # Demand & gap
        peak_visitors = int(meta["capacity"] * 1.25)
        schedule = MATCH_SCHEDULE.get(city, {"group": 6, "knockout": 1, "round": "Group"})
        total_games = schedule["group"] + schedule["knockout"]
        wc_multiplier = 2.8 + (total_games / 20)
        projected_wc = int(avg_visits * wc_multiplier) if avg_visits > 0 else 0
        gap_pct = max(0.0, (100 - transit_score) * (1 + max(0, temp - 25) / 35))

        # Economic impact: capacity × attendance rate × per-visitor spend × multiplier
        # Benchmarks: 95% WC attendance, $280/visitor/match, 1.42 regional multiplier
        economic_impact_m = round(meta["capacity"] * 0.95 * 280 * 1.42 * total_games / 1e6, 0)

        # Heat-illness risk: visitors exposed to heat_idx > 34°C threshold
        heat_idx_val = temp + 0.5 * max(0, hum - 40) * (temp / 30)
        heat_risk_pct = max(0.0, (heat_idx_val - 28) / 20) if heat_idx_val > 28 else 0.0
        heat_risk_visitors = int(peak_visitors * heat_risk_pct)

        rows.append({
            "city": city,
            "state": meta["state"],
            "lat": meta["lat"],
            "lon": meta["lon"],
            "venue": meta["venue"],
            "capacity": meta["capacity"],
            "games": total_games,
            "deepest_round": schedule["round"],
            "transit_score": transit_score,
            "transit_score_expert": meta["transit_score"],
            "transit_source": transit_source,
            "heat_score": round(heat_score, 1),
            "uhi_score": round(uhi_score, 1),
            "accessibility_score": access_score,
            "composite_score": round(composite, 1),
            "avg_temp_c": climate["avg_temp_c"],
            "max_temp_c": climate["max_temp_c"],
            "humidity": climate["humidity"],
            "avg_uhi": round(avg_uhi, 2),
            "p90_uhi": round(p90_uhi, 2),
            "avg_daily_visits": int(avg_visits),
            "peak_daily_visits": int(peak_visits),
            "peak_visitors": peak_visitors,
            "projected_wc_demand": projected_wc,
            "first_last_mile_gap": round(gap_pct, 1),
            "transit_mode": meta["transit_mode"],
            "market_key": mk,
            "economic_impact_m": economic_impact_m,
            "heat_risk_visitors": heat_risk_visitors,
            # GTFS-derived stop-density fields
            "stops_0_5mi": gtfs.get("stops_0_5mi", 0),
            "stops_1mi":   gtfs.get("stops_1mi", 0),
            "stops_2mi":   gtfs.get("stops_2mi", 0),
            "nearest_stop_mi": gtfs.get("nearest_stop_mi", 99.0),
            "gtfs_agencies": ", ".join(gtfs.get("agencies", ["estimated"])),
        })

    return pd.DataFrame(rows).sort_values("composite_score", ascending=False).reset_index(drop=True)


def apply_weights(metrics_df, weights):
    """Recompute composite_score in place with user-adjustable weights (no new data load)."""
    total_w = sum(weights.values())
    tw = weights["transit"] / total_w
    hw = weights["heat"] / total_w
    uw = weights["uhi"] / total_w
    aw = weights["access"] / total_w
    out = metrics_df.copy()
    out["composite_score"] = (
        out["transit_score"] * tw
        + out["heat_score"] * hw
        + out["uhi_score"] * uw
        + out["accessibility_score"] * aw
    ).round(1)
    return out.sort_values("composite_score", ascending=False).reset_index(drop=True), tw


# ── Helpers ──────────────────────────────────────────────────────────────────

def score_color(v):
    if v >= 70:
        return "#4ade80"
    if v >= 50:
        return "#facc15"
    return "#f87171"


def score_class(v):
    if v >= 70:
        return "score-hi"
    if v >= 50:
        return "score-md"
    return "score-lo"


def kpi_html(value, label):
    return f"""<div class="kpi-card">
  <div class="kpi-val">{value}</div>
  <div class="kpi-sub">{label}</div>
</div>"""


def demand_time_series(visits_df, city_name, meta):
    """Build a demand forecast chart for a single city."""
    mk = meta["market_key"]
    v = visits_df[visits_df["market"].str.contains(mk, case=False, na=False)].copy()

    if v.empty:
        return None

    v = v.sort_values("date")
    v["7d_avg"] = v["daily_visits"].rolling(7, min_periods=1).mean()

    # World Cup period: June 11 – July 19, 2026
    wc_start = pd.Timestamp("2026-06-11")
    wc_end = pd.Timestamp("2026-07-19")
    baseline = v["daily_visits"].mean()
    games = MATCH_SCHEDULE.get(city_name, {}).get("group", 6) + MATCH_SCHEDULE.get(city_name, {}).get("knockout", 1)
    multiplier = 2.8 + games / 20

    # Synthetic WC projection band
    proj_dates = pd.date_range(wc_start, wc_end, freq="D")
    proj_lo = baseline * 1.5
    proj_hi = baseline * multiplier
    proj_mid = baseline * (1.5 + (multiplier - 1.5) / 2)

    fig = go.Figure()

    # Historical visits
    fig.add_trace(go.Scatter(
        x=v["date"], y=v["daily_visits"],
        mode="lines", name="Actual Visits",
        line=dict(color="#38bdf8", width=1.5),
        opacity=0.6,
    ))

    # 7-day rolling average
    fig.add_trace(go.Scatter(
        x=v["date"], y=v["7d_avg"],
        mode="lines", name="7-Day Avg",
        line=dict(color="#818cf8", width=2.5),
    ))

    # WC forecast band
    fig.add_trace(go.Scatter(
        x=list(proj_dates) + list(reversed(proj_dates)),
        y=[proj_hi] * len(proj_dates) + [proj_lo] * len(proj_dates),
        fill="toself", fillcolor="rgba(250, 204, 21, 0.12)",
        line=dict(color="rgba(0,0,0,0)"),
        name="WC Demand Range",
        showlegend=True,
    ))

    fig.add_trace(go.Scatter(
        x=proj_dates, y=[proj_mid] * len(proj_dates),
        mode="lines", name=f"WC Forecast ({multiplier:.1f}× baseline)",
        line=dict(color="#facc15", width=2, dash="dot"),
    ))

    # Event window shading
    fig.add_vrect(
        x0=wc_start, x1=wc_end,
        fillcolor="rgba(250, 204, 21, 0.05)",
        layer="below", line_width=0,
    )
    fig.add_annotation(
        x=wc_start + (wc_end - wc_start) / 2,
        y=proj_hi * 1.05,
        text="⚽ FIFA World Cup 2026",
        showarrow=False,
        font=dict(color="#facc15", size=12),
    )

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=-0.15, font=dict(size=11)),
        yaxis_title="Daily Visits",
        height=360,
        xaxis=dict(gridcolor="#1e3a5f"),
        yaxis=dict(gridcolor="#1e3a5f"),
    )
    return fig
