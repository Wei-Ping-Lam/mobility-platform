"""
FIFA 2026 Host City Mobility Readiness Platform
Track 1: Transportation & Access
Rice World Cup Hackathon 2026
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import glob
import json
from pathlib import Path

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="FIFA 2026 Mobility Readiness",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_ROOT = Path(__file__).parent.parent
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
body, [data-testid="stAppViewContainer"] { background: #07111f; }
[data-testid="stSidebar"] { background: #0d1f33; border-right: 1px solid #1e3a5f; }
[data-testid="stSidebar"] * { color: #c9d8e8 !important; }
h1,h2,h3,h4 { color: #ffffff !important; letter-spacing: -0.02em; }
p, li, label { color: #c9d8e8; }
.kpi-row { display: flex; gap: 12px; margin-bottom: 24px; }
.kpi-card {
    flex: 1;
    background: linear-gradient(145deg, #0f2136, #0a1929);
    border: 1px solid #1e4a7a;
    border-radius: 14px;
    padding: 18px 20px;
    text-align: center;
}
.kpi-val  { font-size: 2.1rem; font-weight: 800; color: #38bdf8; line-height: 1; }
.kpi-sub  { font-size: 0.72rem; color: #7fb3d3; text-transform: uppercase;
            letter-spacing: 0.1em; margin-top: 6px; }
.score-hi { color: #4ade80; font-weight: 700; }
.score-md { color: #facc15; font-weight: 700; }
.score-lo { color: #f87171; font-weight: 700; }
.city-pill {
    display: inline-block;
    background: #0f3460; color: #60a5fa;
    border-radius: 20px; padding: 3px 12px;
    font-size: 0.8rem; font-weight: 600;
    margin: 2px;
}
.stTabs [data-baseweb="tab-list"] { background: #0d1f33; border-radius: 10px; padding: 4px; }
.stTabs [data-baseweb="tab"]      { color: #7fb3d3; border-radius: 8px; }
.stTabs [aria-selected="true"]    { background: #1e4a7a !important; color: #ffffff !important; }
.stDataFrame { border-radius: 10px; overflow: hidden; }
div[data-testid="metric-container"] { background: #0f2136; border-radius: 10px; padding: 8px 12px; }
</style>
""", unsafe_allow_html=True)

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

PLOTLY_TEMPLATE = "plotly_dark"
MAP_STYLE = "carto-darkmatter"

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

        # Composite mobility readiness (0–100)
        composite = (
            transit_score * 0.35
            + heat_score * 0.20
            + uhi_score * 0.15
            + access_score * 0.30
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


# ── Main App ─────────────────────────────────────────────────────────────────

# ─ Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ FIFA 2026 Mobility")
    st.markdown("**Track 1 — Transportation & Access**")
    st.divider()

    city_options = ["All Cities"] + sorted(HOST_CITIES.keys())
    selected_city = st.selectbox("Focus City", city_options, index=0)

    st.divider()
    st.markdown("**Readiness Score Weights**")
    w_transit = st.slider("Transit Infrastructure", 0.10, 0.60, 0.35, 0.05)
    w_heat    = st.slider("Heat/Climate",           0.05, 0.40, 0.20, 0.05)
    w_uhi     = st.slider("Urban Heat Island",      0.05, 0.30, 0.15, 0.05)
    w_access  = st.slider("Venue Accessibility",    0.10, 0.50, 0.30, 0.05)

    # Normalize weights
    total_w = w_transit + w_heat + w_uhi + w_access
    if abs(total_w - 1.0) > 0.01:
        st.caption(f"⚠ Weights sum to {total_w:.2f}; normalizing to 1.0")

    st.divider()
    st.caption("Data: Veraset/SafeGraph · Urban Heat Index · Weather observations")
    st.caption("Rice University World Cup Hackathon 2026")


# ─ Load data ─────────────────────────────────────────────────────────────────
visits_df      = load_store_visits()
visits_cat_df  = load_store_visits_by_category()
uhi_df         = load_uhi()
origins_df     = load_spend_origins()

# Use a stable hash so cache is only busted when raw data changes
_vh = str(len(visits_df))
_uh = str(len(uhi_df))
metrics_df = build_city_metrics(_vh, _uh)

# Recompute composite with user-defined weights (no new data load)
tw = w_transit / total_w
hw = w_heat    / total_w
uw = w_uhi     / total_w
aw = w_access  / total_w
metrics_df["composite_score"] = (
    metrics_df["transit_score"]       * tw
    + metrics_df["heat_score"]        * hw
    + metrics_df["uhi_score"]         * uw
    + metrics_df["accessibility_score"] * aw
).round(1)
metrics_df = metrics_df.sort_values("composite_score", ascending=False).reset_index(drop=True)

# Filter if a single city is chosen
display_df = (
    metrics_df[metrics_df["city"] == selected_city]
    if selected_city != "All Cities"
    else metrics_df
)

# ─ Header ────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='text-align:center;font-size:2.2rem;'>⚽ FIFA 2026 Host City Mobility Readiness Platform</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align:center;color:#7fb3d3;margin-top:-10px;'>"
    "Predicting visitor movement · Identifying first/last-mile gaps · "
    "Comparing transit resilience across all 11 US host cities</p>",
    unsafe_allow_html=True,
)
st.divider()

# ─ Top KPIs ──────────────────────────────────────────────────────────────────
us_games         = metrics_df["games"].sum()   # 78 — US-hosted matches
avg_readiness    = metrics_df["composite_score"].mean()
total_econ_b     = metrics_df["economic_impact_m"].sum() / 1000
total_heat_risk  = metrics_df["heat_risk_visitors"].sum()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(kpi_html("11", "US Host Cities"), unsafe_allow_html=True)
with col2:
    st.markdown(kpi_html(f"{us_games}", "US-Hosted Matches"), unsafe_allow_html=True)
with col3:
    st.markdown(kpi_html(f"${total_econ_b:.1f}B", "Projected Economic Impact"), unsafe_allow_html=True)
with col4:
    st.markdown(kpi_html(f"{total_heat_risk:,}", "Visitors at Heat Risk"), unsafe_allow_html=True)
with col5:
    st.markdown(kpi_html(f"{avg_readiness:.0f}/100", "Avg Mobility Readiness"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─ Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🗺️ City Overview",
    "📈 Visitor Demand",
    "⚠️ Gap Analysis",
    "📊 City Comparison",
    "🔧 Intervention Planner",
    "🌱 Legacy & Scalability",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — CITY OVERVIEW MAP
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    col_map, col_detail = st.columns([2, 1])

    with col_map:
        st.markdown("### Mobility Readiness by Host City")
        st.caption("Bubble size = matches hosted · Color = composite readiness score")

        fig_map = px.scatter_mapbox(
            display_df,
            lat="lat", lon="lon",
            size="games",
            color="composite_score",
            color_continuous_scale=["#ef4444", "#facc15", "#22c55e"],
            range_color=[30, 95],
            size_max=28,
            hover_name="city",
            hover_data={
                "venue": True,
                "composite_score": ":.1f",
                "transit_score": True,
                "games": True,
                "lat": False, "lon": False,
            },
            zoom=3.0,
            center={"lat": 38.5, "lon": -96},
            mapbox_style=MAP_STYLE,
            height=480,
        )
        fig_map.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_colorbar=dict(
                title="Readiness",
                tickvals=[30, 50, 70, 90],
                ticktext=["30 Low", "50", "70", "90 High"],
                thickness=12,
                len=0.7,
            ),
        )
        # Add city labels
        fig_map.add_trace(go.Scattermapbox(
            lat=display_df["lat"],
            lon=display_df["lon"],
            mode="text",
            text=display_df["city"],
            textfont=dict(size=10, color="white"),
            textposition="top center",
            hoverinfo="skip",
            showlegend=False,
        ))
        st.plotly_chart(fig_map, width='stretch')

    with col_detail:
        st.markdown("### City Rankings")
        for _, row in display_df.iterrows():
            sc = row["composite_score"]
            cl = score_class(sc)
            icon = "🟢" if sc >= 70 else "🟡" if sc >= 50 else "🔴"
            st.markdown(
                f"{icon} **{row['city']}**  "
                f"<span class='{cl}'>{sc:.0f}</span>/100 · "
                f"{row['games']} games · {row['deepest_round']}",
                unsafe_allow_html=True,
            )
            st.progress(int(sc), text=None)

        st.divider()
        st.markdown("#### Score Breakdown")
        if selected_city != "All Cities":
            row = metrics_df[metrics_df["city"] == selected_city].iloc[0]
        else:
            row = metrics_df.iloc[0]  # top city

        radar_fig = go.Figure(go.Scatterpolar(
            r=[row["transit_score"], row["heat_score"],
               row["uhi_score"], row["accessibility_score"], row["transit_score"]],
            theta=["Transit", "Heat Safety", "Low UHI", "Accessibility", "Transit"],
            fill="toself",
            fillcolor="rgba(56,189,248,0.15)",
            line=dict(color="#38bdf8", width=2),
            name=row["city"],
        ))
        radar_fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="#1e3a5f"),
                angularaxis=dict(gridcolor="#1e3a5f"),
                bgcolor="rgba(0,0,0,0)",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            template=PLOTLY_TEMPLATE,
            showlegend=False,
            height=260,
            margin=dict(l=20, r=20, t=20, b=20),
        )
        st.plotly_chart(radar_fig, width='stretch')
        st.caption(f"Profile for **{row['city']}** · Venue: {row['venue']}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — VISITOR DEMAND FORECAST
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Visitor Demand Prediction & World Cup Surge Forecast")
    st.caption(
        "**Data note:** Daily visits = mobile-device-derived foot traffic to retail and commercial locations "
        "(restaurants, entertainment, services) across the metro market area — sourced from Veraset/SafeGraph. "
        "This is a proxy for overall city mobility demand, not stadium attendance. "
        "World Cup surge multipliers are **category-specific**: derived by blending published FIFA economic-impact "
        "benchmarks (US Travel Assoc. 2019; Baade & Matheson 2016; FIFA 2022/2018 LOC Reports) with each "
        "category's historical p90/median variability from the actual store-visits dataset."
    )

    col_ts, col_peak = st.columns([3, 1])

    with col_ts:
        if visits_df.empty:
            st.warning("Store visit data not loaded. Check data path and retry.")
        else:
            focus = selected_city if selected_city != "All Cities" else "Dallas"
            ts_city = st.selectbox("Select city for time-series view", list(HOST_CITIES.keys()),
                                   index=list(HOST_CITIES.keys()).index(focus)
                                   if focus in HOST_CITIES else 0,
                                   key="ts_city")
            ts_meta = HOST_CITIES[ts_city]
            fig_ts = demand_time_series(visits_df, ts_city, ts_meta)
            if fig_ts:
                st.plotly_chart(fig_ts, width='stretch')
            else:
                st.info("No visit data found for this market in the loaded partitions.")

    with col_peak:
        st.markdown("#### Peak Match Day Estimates")
        st.caption("Capacity × 1.25 surge factor")
        for _, row in display_df.sort_values("capacity", ascending=False).iterrows():
            pct_transit = row["transit_score"]
            by_transit = int(row["peak_visitors"] * pct_transit / 100)
            by_car = row["peak_visitors"] - by_transit
            st.metric(
                label=row["city"],
                value=f"{row['peak_visitors']:,}",
                delta=f"{row['games']} matches",
            )

    st.divider()
    st.markdown("#### Category-Specific World Cup Demand Surge")
    st.caption(
        "Multiplier = FIFA category benchmark × local variability adjustment (p90/median from store-visits data). "
        "Only FIFA-relevant categories shown (benchmark > 1.2×). "
        "Sources: [A] US Travel Assoc. 2019 · [B] Baade & Matheson, J. Sports Econ. 2016 · "
        "[C] FIFA 2022 LOC Report · [D] FIFA 2018 Economic Impact Assessment"
    )

    surge_city = st.selectbox(
        "Select city for category breakdown",
        list(HOST_CITIES.keys()),
        index=list(HOST_CITIES.keys()).index(
            selected_city if selected_city != "All Cities" else "Dallas"
        ),
        key="surge_city",
    )
    surge_mk = HOST_CITIES[surge_city]["market_key"]
    surge_df = compute_category_surge(visits_cat_df, surge_mk)

    if not surge_df.empty:
        surge_show = surge_df[surge_df["Category"].isin(FIFA_RELEVANT_CATEGORIES)].copy()
        if surge_show.empty:
            surge_show = surge_df.head(8)

        col_surge1, col_surge2 = st.columns([3, 2])

        with col_surge1:
            surge_melt = surge_show.melt(
                id_vars="Category",
                value_vars=["Baseline Visits/Day", "Projected Visits/Day"],
                var_name="Scenario", value_name="Daily Visits",
            )
            surge_melt["Category"] = surge_melt["Category"].str.replace(
                " and ", " & ", regex=False
            )
            fig_surge = px.bar(
                surge_melt,
                x="Daily Visits", y="Category",
                color="Scenario",
                barmode="group",
                orientation="h",
                color_discrete_map={
                    "Baseline Visits/Day":   "#475569",
                    "Projected Visits/Day":  "#38bdf8",
                },
                labels={"Daily Visits": "Daily Visits", "Category": ""},
                template=PLOTLY_TEMPLATE,
                height=max(280, len(surge_show) * 55),
            )
            fig_surge.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", y=-0.15),
                xaxis=dict(gridcolor="#1e3a5f"),
                yaxis=dict(gridcolor="#1e3a5f"),
            )
            st.plotly_chart(fig_surge, width="stretch")

        with col_surge2:
            st.markdown("**Multiplier breakdown**")
            tbl_cols = ["Category", "FIFA Benchmark", "Hist. Variability",
                        "Projected Multiplier", "Source"]
            tbl = surge_show[tbl_cols].copy()
            tbl["Category"] = tbl["Category"].str.replace(" and ", " & ", regex=False)
            tbl["Projected Multiplier"] = tbl["Projected Multiplier"].apply(
                lambda x: f"{x:.2f}×"
            )
            tbl["FIFA Benchmark"] = tbl["FIFA Benchmark"].apply(lambda x: f"{x:.1f}×")
            tbl["Hist. Variability"] = tbl["Hist. Variability"].apply(
                lambda x: f"{x:.2f}×"
            )
            st.dataframe(tbl, hide_index=True, width="stretch")
    else:
        st.info("Category data not available for this market in the loaded partitions.")

    st.divider()
    st.markdown("#### Visitor Origin Intelligence")
    st.caption(
        "Home-state origins of consumers visiting each market — sourced from Veraset/SafeGraph spend-pattern mobility data. "
        "Reveals existing fan corridors and informs intercity transport planning."
    )

    if not origins_df.empty:
        col_orig1, col_orig2 = st.columns([1, 2])
        with col_orig1:
            # Market name mapping from spend dataset to HOST_CITIES
            market_map = {
                "San Francisco Bay Area": "San Francisco",
                "New York/New Jersey": "New York/NJ",
                "Los Angeles": "Los Angeles",
                "Dallas": "Dallas",
                "Houston": "Houston",
                "Atlanta": "Atlanta",
                "Miami": "Miami",
                "Seattle": "Seattle",
                "Boston": "Boston",
                "Kansas City": "Kansas City",
                "Philadelphia": "Philadelphia",
            }
            available_markets = [m for m in origins_df["market"].unique() if m in market_map]
            origin_market = st.selectbox(
                "Select market",
                available_markets,
                key="origin_market",
            )
        with col_orig2:
            mkt_data = (
                origins_df[origins_df["market"] == origin_market]
                .sort_values("count", ascending=False)
                .head(12)
            )
            fig_orig = px.bar(
                mkt_data,
                x="count", y="home_state",
                orientation="h",
                color="count",
                color_continuous_scale=["#1e4a7a", "#38bdf8"],
                labels={"count": "Visitor Count", "home_state": "Home State"},
                template=PLOTLY_TEMPLATE,
                height=320,
            )
            fig_orig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                coloraxis_showscale=False,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(gridcolor="#1e3a5f"),
                yaxis=dict(gridcolor="#1e3a5f"),
            )
            st.plotly_chart(fig_orig, width='stretch')
    else:
        st.info("Visitor origin data not loaded — check spend-patterns-rice/ data path.")

    # Economic impact by city
    st.divider()
    st.markdown("#### Projected Economic Impact by Host City")
    st.caption("Estimate: venue capacity × 95% attendance × $280/visitor/match-day × 1.42 regional multiplier (sports economics benchmark)")
    econ_df = display_df[["city", "economic_impact_m", "games"]].sort_values("economic_impact_m", ascending=False).copy()
    econ_df["impact_label"] = econ_df["economic_impact_m"].apply(lambda x: f"${x:,.0f}M")
    fig_econ = px.bar(
        econ_df, x="city", y="economic_impact_m",
        color="economic_impact_m",
        color_continuous_scale=["#1e4a7a", "#22c55e"],
        text="impact_label",
        labels={"economic_impact_m": "Impact ($M)", "city": ""},
        template=PLOTLY_TEMPLATE,
        height=320,
    )
    fig_econ.update_traces(textposition="outside", textfont_color="white")
    fig_econ.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(gridcolor="#1e3a5f"),
        yaxis=dict(title="Economic Impact ($M)", gridcolor="#1e3a5f"),
    )
    st.plotly_chart(fig_econ, width='stretch')


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — GAP ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### First/Last-Mile Gap Analysis")
    st.caption(
        "Gap Score = function of transit under-capacity, summer heat, and urban heat island intensity. "
        "Higher = greater unmet mobility need."
    )

    col_gap1, col_gap2 = st.columns([3, 2])

    with col_gap1:
        # Bubble: transit score vs gap score, sized by capacity
        fig_gap = px.scatter(
            display_df,
            x="transit_score", y="first_last_mile_gap",
            size="capacity", color="avg_temp_c",
            color_continuous_scale="RdYlGn_r",
            hover_name="city",
            hover_data={"venue": True, "avg_uhi": True, "capacity": ":,"},
            size_max=40,
            labels={
                "transit_score": "Transit Infrastructure Score (0–100)",
                "first_last_mile_gap": "First/Last-Mile Gap Score",
                "avg_temp_c": "Avg Summer Temp (°C)",
            },
            template=PLOTLY_TEMPLATE,
            height=400,
        )
        # Quadrant lines
        fig_gap.add_hline(y=40, line_dash="dot", line_color="#475569", annotation_text="High gap threshold")
        fig_gap.add_vline(x=60, line_dash="dot", line_color="#475569", annotation_text="Low transit threshold")

        # Quadrant labels
        fig_gap.add_annotation(x=25, y=70, text="⚠️ HIGH PRIORITY\nWeak transit + High gap",
                                showarrow=False, font=dict(size=10, color="#f87171"), align="center")
        fig_gap.add_annotation(x=85, y=20, text="✅ RESILIENT\nStrong transit + Low gap",
                                showarrow=False, font=dict(size=10, color="#4ade80"), align="center")

        fig_gap.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#1e3a5f"),
            yaxis=dict(gridcolor="#1e3a5f"),
        )
        st.plotly_chart(fig_gap, width='stretch')

    with col_gap2:
        st.markdown("#### Heat Stress × Visitor Density Risk")
        # Scatter: UHI vs heat_score colored by composite
        fig_heat = px.scatter(
            display_df,
            x="avg_uhi", y="avg_temp_c",
            size="games",
            color="composite_score",
            color_continuous_scale=["#ef4444", "#facc15", "#22c55e"],
            range_color=[30, 95],
            hover_name="city",
            size_max=25,
            labels={
                "avg_uhi": "Avg Urban Heat Island (°C above rural)",
                "avg_temp_c": "June–July Avg Temperature (°C)",
                "composite_score": "Readiness",
            },
            template=PLOTLY_TEMPLATE,
            height=280,
        )
        fig_heat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#1e3a5f"),
            yaxis=dict(gridcolor="#1e3a5f"),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_heat, width='stretch')

        st.markdown("#### Gap Score Rankings")
        gap_table = display_df[["city", "first_last_mile_gap", "transit_score", "avg_temp_c"]].sort_values(
            "first_last_mile_gap", ascending=False
        )
        for _, r in gap_table.iterrows():
            bar_pct = int(min(r["first_last_mile_gap"], 100))
            cl = "score-lo" if r["first_last_mile_gap"] > 50 else "score-md" if r["first_last_mile_gap"] > 30 else "score-hi"
            st.markdown(
                f"**{r['city']}** — <span class='{cl}'>{r['first_last_mile_gap']:.0f}</span>",
                unsafe_allow_html=True
            )
            st.progress(bar_pct)

    st.divider()
    st.markdown("#### The Transit Illusion: City Reputation vs. Venue Reality")
    st.caption(
        "Many cities are known for world-class transit — but their FIFA venues sit in "
        "suburban areas far from rail coverage. GTFS stop-count data reveals the gap between "
        "a city's transit reputation and actual match-day access."
    )

    illusion_rows = []
    for _c, _m in HOST_CITIES.items():
        _row = metrics_df[metrics_df["city"] == _c]
        if _row.empty:
            continue
        illusion_rows.append({
            "City": _c,
            "Expert Reputation": _m["transit_score"],
            "GTFS Venue Reality": int(_row["transit_score"].values[0]),
            "Gap": _m["transit_score"] - int(_row["transit_score"].values[0]),
        })
    illusion_df = pd.DataFrame(illusion_rows).sort_values("Gap", ascending=False)

    col_ill1, col_ill2 = st.columns([3, 2])
    with col_ill1:
        fig_ill = go.Figure()
        # diagonal reference line (y=x)
        fig_ill.add_trace(go.Scatter(
            x=[0, 100], y=[0, 100],
            mode="lines",
            line=dict(color="#475569", dash="dash", width=1),
            showlegend=False, hoverinfo="skip",
        ))
        fig_ill.add_annotation(
            x=80, y=83, text="y = x (reality matches reputation)",
            showarrow=False, font=dict(size=9, color="#64748b"), textangle=-38,
        )
        for _, r in illusion_df.iterrows():
            color = "#f87171" if r["Gap"] > 30 else "#facc15" if r["Gap"] > 0 else "#4ade80"
            fig_ill.add_trace(go.Scatter(
                x=[r["Expert Reputation"]], y=[r["GTFS Venue Reality"]],
                mode="markers+text",
                marker=dict(size=16, color=color, line=dict(width=1, color="white")),
                text=[r["City"]],
                textposition="top center",
                textfont=dict(size=9, color="white"),
                name=r["City"],
                showlegend=False,
                hovertemplate=(
                    f"<b>{r['City']}</b><br>"
                    f"Expert estimate: {r['Expert Reputation']}<br>"
                    f"GTFS venue reality: {r['GTFS Venue Reality']}<br>"
                    f"Gap: {r['Gap']}<extra></extra>"
                ),
            ))
        fig_ill.add_annotation(x=12, y=75, text="✅ Better than expected",
                               showarrow=False, font=dict(size=10, color="#4ade80"))
        fig_ill.add_annotation(x=80, y=12, text="⚠️ Transit Illusion Zone",
                               showarrow=False, font=dict(size=10, color="#f87171"))
        fig_ill.update_layout(
            xaxis_title="Expert Transit Reputation (0–100)",
            yaxis_title="GTFS Venue Reality Score (0–100)",
            xaxis=dict(range=[0, 105], gridcolor="#1e3a5f"),
            yaxis=dict(range=[0, 105], gridcolor="#1e3a5f"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            template=PLOTLY_TEMPLATE,
            height=380,
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_ill, width='stretch')

    with col_ill2:
        st.markdown("**Illusion Gap Rankings**")
        st.caption("Positive gap = venue access worse than city reputation implies")
        for _, r in illusion_df.iterrows():
            gap_val = r["Gap"]
            color_cls = "score-lo" if gap_val > 30 else "score-md" if gap_val > 10 else "score-hi"
            direction = "▼" if gap_val > 0 else "▲"
            st.markdown(
                f"**{r['City']}** — Rep: {r['Expert Reputation']} → Reality: {r['GTFS Venue Reality']} "
                f"<span class='{color_cls}'>{direction}{abs(gap_val)}</span>",
                unsafe_allow_html=True,
            )
        st.divider()
        st.markdown(
            "**Key insight:** New York/NJ (MetLife) and Boston (Gillette) are famous for "
            "transit but their venues are suburban — match-day fans are overwhelmingly car-dependent. "
            "Seattle and Atlanta are the true leaders at the venue level.",
            unsafe_allow_html=False,
        )

    st.divider()
    st.markdown("#### Transit Stop Density Around Each Venue (GTFS Live Data)")
    st.caption("Stops counted within walking distance rings of the actual stadium — sourced from each city's transit agency GTFS feed.")

    stop_df = display_df[["city", "stops_0_5mi", "stops_1mi", "stops_2mi",
                           "nearest_stop_mi", "transit_source", "gtfs_agencies"]].copy()
    stop_df = stop_df.sort_values("stops_1mi", ascending=False)

    stop_melt = stop_df.melt(
        id_vars=["city", "transit_source"],
        value_vars=["stops_0_5mi", "stops_1mi", "stops_2mi"],
        var_name="radius", value_name="stop_count",
    )
    stop_melt["radius"] = stop_melt["radius"].map({
        "stops_0_5mi": "Within 0.5 mi",
        "stops_1mi":   "Within 1 mi",
        "stops_2mi":   "Within 2 mi",
    })

    fig_stops = px.bar(
        stop_melt,
        x="city", y="stop_count", color="radius",
        barmode="group",
        color_discrete_map={
            "Within 0.5 mi": "#38bdf8",
            "Within 1 mi":   "#818cf8",
            "Within 2 mi":   "#c084fc",
        },
        labels={"stop_count": "Transit Stops", "city": "", "radius": ""},
        template=PLOTLY_TEMPLATE,
        height=340,
        text_auto=True,
    )
    fig_stops.update_traces(textposition="outside", textfont=dict(size=9, color="white"))
    fig_stops.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=-0.2),
        xaxis=dict(gridcolor="#1e3a5f"),
        yaxis=dict(gridcolor="#1e3a5f"),
    )
    st.plotly_chart(fig_stops, width='stretch')

    # Nearest stop callout cards
    cols = st.columns(len(display_df))
    for col, (_, r) in zip(cols, stop_df.iterrows()):
        dist = r["nearest_stop_mi"]
        label = "🟢" if dist < 0.25 else "🟡" if dist < 1.0 else "🔴"
        est = " *" if r["transit_source"] == "estimated" else ""
        with col:
            st.metric(
                label=r["city"] + est,
                value=f"{dist:.2f} mi" if dist < 90 else "N/A",
                delta="nearest stop",
                delta_color="off",
            )
    st.caption("\\* Estimated (GTFS not available) · Distances from venue centroid to nearest transit stop")

    st.divider()
    st.markdown("#### Detailed Gap Metrics Table")
    tbl = display_df[["city", "venue", "capacity", "games", "transit_score",
                       "transit_source", "stops_0_5mi", "nearest_stop_mi",
                       "first_last_mile_gap", "avg_temp_c", "avg_uhi",
                       "transit_mode"]].copy()
    tbl.columns = ["City", "Venue", "Capacity", "Games", "Transit Score",
                   "Score Source", "Stops <=0.5mi", "Nearest Stop (mi)",
                   "Gap Score", "Avg Temp °C", "Avg UHI", "Primary Transit"]
    tbl = tbl.sort_values("Gap Score", ascending=False)
    st.dataframe(
        tbl.style
           .background_gradient(subset=["Gap Score"], cmap="RdYlGn_r", vmin=0, vmax=80)
           .background_gradient(subset=["Transit Score"], cmap="RdYlGn", vmin=5, vmax=100)
           .background_gradient(subset=["Stops <=0.5mi"], cmap="Blues", vmin=0, vmax=30)
           .format({"Capacity": "{:,.0f}", "Gap Score": "{:.1f}",
                    "Avg Temp °C": "{:.1f}", "Avg UHI": "{:.2f}",
                    "Nearest Stop (mi)": "{:.3f}"}),
        width='stretch',
        hide_index=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — CITY COMPARISON
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### Multi-City Mobility Comparison")

    col_radar, col_bar = st.columns([1, 1])

    with col_radar:
        st.markdown("#### Radar: All Cities Across 4 Dimensions")
        categories = ["Transit Score", "Heat Safety", "Low UHI", "Accessibility"]
        radar_fig = go.Figure()
        colors = px.colors.qualitative.Plotly

        for i, (_, row) in enumerate(display_df.iterrows()):
            vals = [row["transit_score"], row["heat_score"],
                    row["uhi_score"], row["accessibility_score"]]
            vals_closed = vals + [vals[0]]
            cats_closed = categories + [categories[0]]
            radar_fig.add_trace(go.Scatterpolar(
                r=vals_closed,
                theta=cats_closed,
                mode="lines+markers",
                name=row["city"],
                line=dict(color=colors[i % len(colors)], width=1.5),
                marker=dict(size=4),
                opacity=0.8,
            ))

        radar_fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="#1e3a5f", tickfont=dict(size=9)),
                angularaxis=dict(gridcolor="#1e3a5f"),
                bgcolor="rgba(0,0,0,0)",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            template=PLOTLY_TEMPLATE,
            legend=dict(font=dict(size=9), orientation="v", x=1.05),
            height=440,
            margin=dict(l=40, r=120, t=20, b=20),
        )
        st.plotly_chart(radar_fig, width='stretch')

    with col_bar:
        st.markdown("#### Composite Readiness Score")
        fig_bar = px.bar(
            display_df.sort_values("composite_score"),
            x="composite_score", y="city",
            orientation="h",
            color="composite_score",
            color_continuous_scale=["#ef4444", "#facc15", "#22c55e"],
            range_color=[30, 95],
            text="composite_score",
            labels={"composite_score": "Score", "city": ""},
            template=PLOTLY_TEMPLATE,
            height=420,
        )
        fig_bar.update_traces(texttemplate="%{text:.1f}", textposition="outside", textfont_color="white")
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
            margin=dict(l=0, r=40, t=10, b=0),
            xaxis=dict(gridcolor="#1e3a5f", range=[0, 105]),
            yaxis=dict(gridcolor="#1e3a5f"),
        )
        st.plotly_chart(fig_bar, width='stretch')

    st.divider()
    st.markdown("#### Component Breakdown Heatmap")

    heat_data = display_df.set_index("city")[
        ["transit_score", "heat_score", "uhi_score", "accessibility_score", "composite_score"]
    ].rename(columns={
        "transit_score": "Transit", "heat_score": "Heat Safety",
        "uhi_score": "Low UHI", "accessibility_score": "Venue Access",
        "composite_score": "COMPOSITE",
    })

    fig_hm = px.imshow(
        heat_data.T,
        color_continuous_scale="RdYlGn",
        zmin=0, zmax=100,
        text_auto=".0f",
        aspect="auto",
        template=PLOTLY_TEMPLATE,
        height=280,
    )
    fig_hm.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(tickangle=-30),
    )
    st.plotly_chart(fig_hm, width='stretch')


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — INTERVENTION PLANNER
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("### Mobility Intervention Scenario Planner")
    st.caption("Model the impact of transit investments on mobility stress and CO₂ reduction for a selected city.")

    plan_city = st.selectbox(
        "Select Host City",
        list(HOST_CITIES.keys()),
        index=list(HOST_CITIES.keys()).index(selected_city)
        if selected_city != "All Cities" else 2,
        key="plan_city",
    )
    city_row = metrics_df[metrics_df["city"] == plan_city].iloc[0]

    st.divider()
    col_sliders, col_impact = st.columns([1, 1])

    with col_sliders:
        st.markdown("#### Proposed Interventions")

        shuttle_freq = st.slider(
            "🚌 Event Shuttle Frequency (buses/hour)",
            min_value=0, max_value=60, value=10, step=5,
            help="Dedicated shuttle service to/from venue on match days",
        )
        bike_stations = st.slider(
            "🚲 Bike-Share Stations Near Venue",
            min_value=0, max_value=50, value=5, step=5,
            help="New bike-share docking stations within 1 mile of venue",
        )
        park_ride = st.slider(
            "🅿️ Park & Ride Capacity (spaces)",
            min_value=0, max_value=20000, value=2000, step=1000,
            help="Park-and-ride lots served by dedicated transit",
        )
        pedestrian_infra = st.slider(
            "🚶 Pedestrian Infrastructure Upgrade (%)",
            min_value=0, max_value=100, value=20, step=10,
            help="Shade structures, cooling stations, accessible pathways",
        )

    with col_impact:
        st.markdown("#### Projected Impact")

        base_transit = city_row["transit_score"]
        base_gap = city_row["first_last_mile_gap"]
        base_composite = city_row["composite_score"]
        peak_v = city_row["peak_visitors"]

        # Model improvements
        shuttle_boost   = min(20, shuttle_freq * 0.33)
        bike_boost      = min(8,  bike_stations * 0.16)
        pr_boost        = min(12, park_ride / 1000 * 0.6)
        ped_boost       = min(10, pedestrian_infra * 0.10)
        total_boost     = shuttle_boost + bike_boost + pr_boost + ped_boost

        new_transit     = min(100, base_transit + total_boost)
        new_composite   = min(100, base_composite + total_boost * (w_transit / total_w))
        new_gap         = max(0, base_gap - total_boost * 0.9)

        # Visitors shifted to transit
        base_transit_pct   = base_transit / 100
        new_transit_pct    = new_transit / 100
        shifted_visitors   = int(peak_v * (new_transit_pct - base_transit_pct))

        # CO2 reduction: avg car trip to venue assumed 25 km, 0.21 kg CO2/km
        co2_saved_kg = shifted_visitors * 25 * 0.21
        co2_saved_tonnes = co2_saved_kg / 1000

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Transit Score", f"{new_transit:.0f}/100",
                      delta=f"+{total_boost:.1f}")
            st.metric("Composite Readiness", f"{new_composite:.0f}/100",
                      delta=f"+{new_composite - base_composite:.1f}")
        with c2:
            st.metric("Gap Score", f"{new_gap:.0f}",
                      delta=f"{new_gap - base_gap:.1f}", delta_color="inverse")
            st.metric("Visitors Shifted to Transit", f"{shifted_visitors:,}",
                      delta="per match day")

        st.metric("Est. CO₂ Reduction", f"{co2_saved_tonnes:,.0f} tonnes",
                  delta="per match day vs. baseline", delta_color="normal")

        st.divider()
        # Before/after bar
        before_after = pd.DataFrame({
            "Scenario": ["Baseline", "With Interventions"],
            "Transit Score":       [base_transit,  new_transit],
            "Composite Readiness": [base_composite, new_composite],
            "Gap Score":           [base_gap,       new_gap],
        })
        fig_ba = px.bar(
            before_after.melt(id_vars="Scenario"),
            x="variable", y="value",
            color="Scenario",
            barmode="group",
            color_discrete_map={"Baseline": "#475569", "With Interventions": "#38bdf8"},
            labels={"variable": "", "value": "Score"},
            template=PLOTLY_TEMPLATE,
            height=280,
        )
        fig_ba.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", y=-0.2),
            xaxis=dict(gridcolor="#1e3a5f"),
            yaxis=dict(gridcolor="#1e3a5f", range=[0, 110]),
        )
        st.plotly_chart(fig_ba, width='stretch')

    st.divider()
    # ── Cost & ROI Analysis ───────────────────────────────────────────────────
    st.markdown("#### Investment Cost & Return Analysis")
    st.caption("Capital cost estimates based on US transit infrastructure benchmarks (FTA, NACTO, FHWA)")

    shuttle_capex_per_day  = shuttle_freq * 2880        # $180/bus-hr × 16 hrs
    bike_capex             = bike_stations * 45000       # $45K/station (capital)
    pr_capex               = park_ride * 2800            # $2,800/space (capital)
    ped_capex              = (pedestrian_infra / 10) * 800000  # $800K per 10%
    total_capex            = int(bike_capex + pr_capex + ped_capex)
    total_opex_per_match   = int(shuttle_capex_per_day)

    # Economic return: shifted visitors spend $280/match day + CO₂ social cost ($50/tonne)
    total_games_city       = city_row["games"]
    annual_visitor_return  = shifted_visitors * 280 * total_games_city
    annual_co2_value       = co2_saved_tonnes * total_games_city * 50
    annual_return          = annual_visitor_return + annual_co2_value
    payback_years          = (total_capex / annual_return) if annual_return > 1000 else 99

    col_cost1, col_cost2, col_cost3, col_cost4 = st.columns(4)
    with col_cost1:
        st.metric("Capital Investment", f"${total_capex:,.0f}",
                  delta="one-time capex")
    with col_cost2:
        st.metric("Match-Day Opex", f"${total_opex_per_match:,.0f}",
                  delta="per match")
    with col_cost3:
        st.metric("Annual Economic Return", f"${annual_return:,.0f}",
                  delta=f"visitors + CO₂ value")
    with col_cost4:
        pb = f"{payback_years:.1f} yrs" if payback_years < 50 else "Long-term"
        st.metric("Simple Payback", pb, delta="capital recovery")

    # Cost breakdown bar chart
    cost_items = []
    if bike_capex > 0:
        cost_items.append({"Item": "Bike-Share Stations", "Cost ($)": bike_capex, "Type": "Capital"})
    if pr_capex > 0:
        cost_items.append({"Item": "Park & Ride", "Cost ($)": pr_capex, "Type": "Capital"})
    if ped_capex > 0:
        cost_items.append({"Item": "Pedestrian Infra", "Cost ($)": ped_capex, "Type": "Capital"})
    if shuttle_capex_per_day > 0:
        cost_items.append({"Item": "Shuttle (per match)", "Cost ($)": shuttle_capex_per_day, "Type": "Operating"})
    if cost_items:
        cost_df = pd.DataFrame(cost_items)
        fig_cost = px.bar(
            cost_df, x="Item", y="Cost ($)",
            color="Type",
            color_discrete_map={"Capital": "#38bdf8", "Operating": "#818cf8"},
            text=cost_df["Cost ($)"].apply(lambda v: f"${v:,.0f}"),
            template=PLOTLY_TEMPLATE, height=240,
        )
        fig_cost.update_traces(textposition="outside", textfont_color="white")
        fig_cost.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#1e3a5f"), yaxis=dict(gridcolor="#1e3a5f"),
            legend=dict(orientation="h", y=-0.25),
        )
        st.plotly_chart(fig_cost, width='stretch')

    st.divider()
    st.markdown("#### Recommended Priority Investments")

    gap = city_row["first_last_mile_gap"]
    temp = city_row["avg_temp_c"]
    uhi = city_row["avg_uhi"]
    transit = city_row["transit_score"]

    # Agency-specific recommendations by city
    AGENCY_MAP = {
        "Atlanta": "MARTA (Metropolitan Atlanta Rapid Transit Authority)",
        "Boston": "MBTA (Massachusetts Bay Transportation Authority) + Patriot Place",
        "Dallas": "DART (Dallas Area Rapid Transit) + City of Arlington",
        "Houston": "METRO Houston + Harris County",
        "Kansas City": "RideKC / KCATA",
        "Los Angeles": "LA Metro + City of Inglewood",
        "Miami": "Miami-Dade Transit + MDT",
        "New York/NJ": "NJ Transit + NJDOT + Meadowlands Sports Complex",
        "Philadelphia": "SEPTA + Philadelphia PPA",
        "San Francisco": "VTA + Caltrain + City of Santa Clara",
        "Seattle": "Sound Transit + King County Metro",
    }
    agency = AGENCY_MAP.get(plan_city, "Local transit authority")

    recs = []
    if transit < 50:
        recs.append(("🚌", "High-frequency event shuttles",
                     f"Transit score of {transit:.0f} indicates heavy car dependency. "
                     f"**Implementing agency:** {agency}. "
                     f"Deploy dedicated match-day shuttles from key rail/bus hubs; 15-min frequency can absorb 15–20% of match-day vehicle load."))
    if gap > 50:
        recs.append(("🔗", "First/last-mile micro-mobility",
                     f"Gap score of {gap:.0f} signals poor connections from transit stops to venue. "
                     f"Bike-share and e-scooter docking at the nearest rail station closes this gap. "
                     f"**Estimated cost:** ${bike_stations * 45000:,.0f} for {bike_stations} stations."))
    if temp > 28:
        recs.append(("🌡️", "Cooling corridors & shade canopies",
                     f"June–July average of {temp:.1f}°C poses heat illness risk for pedestrian access routes. "
                     f"Misting stations and tensile shade canopies along pedestrian corridors reduce apparent temperature by 6–10°C. "
                     f"**Implementing agency:** City Public Works + venue operator."))
    if uhi > 5:
        recs.append(("🌳", "Urban greening along transit corridors",
                     f"UHI of {uhi:.1f}°C above rural baseline amplifies heat risk. "
                     f"Tree canopy (target 20% cover on transit corridors) and cool pavements reduce walkway temperatures 3–5°C year-round."))
    recs.append(("📱", "Unified real-time mobility app",
                 "A FIFA 2026 mobility app integrating real-time bus/shuttle arrivals, bike-share availability, "
                 "parking lot status, and crowd-level alerts. Reduces friction for international visitors unfamiliar with local transit. "
                 "**Partners:** transit agencies + FIFA Host City Liaison."))
    recs.append(("🚗", "Dynamic park-and-ride with transit integration",
                 f"Pre-purchased parking + shuttle bundles sold through the FIFA ticketing platform. "
                 f"{park_ride:,} spaces at {park_ride // 50 + 1} sites, served by dedicated express shuttles, can reduce venue-area traffic by {min(40, park_ride // 200)}%."))

    for icon, title, desc in recs:
        with st.expander(f"{icon} {title}"):
            st.markdown(desc)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — LEGACY & SCALABILITY
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown("### Beyond FIFA 2026: Legacy, Scalability & Long-Term Impact")
    st.caption(
        "Transit investments made for FIFA 2026 generate compounding returns for cities, "
        "residents, and future mega-events. This tab quantifies the 10-year legacy value."
    )

    # ── Long-term ROI projection ──────────────────────────────────────────────
    st.markdown("#### 10-Year Transit Investment ROI Projection")
    st.caption(
        "Projects annual economic return of FIFA-driven transit upgrades "
        "assuming 15% ridership growth in year 1, 3% annual growth thereafter, "
        "and $0.80 economic return per passenger-mile."
    )

    legacy_city = st.selectbox(
        "Select city for legacy analysis",
        list(HOST_CITIES.keys()),
        key="legacy_city",
    )
    lc_row = metrics_df[metrics_df["city"] == legacy_city].iloc[0]
    lc_transit = lc_row["transit_score"]
    lc_gap = lc_row["first_last_mile_gap"]
    lc_games = lc_row["games"]

    # Assume city implements full recommended intervention package
    base_capex = (
        max(0, 50 - lc_row["stops_0_5mi"]) * 45000   # bike stations needed
        + max(0, 70 - lc_transit) * 30000              # transit upgrade proxy
        + int(lc_gap) * 15000                          # gap closure cost
    )
    base_capex = max(500000, min(base_capex, 50_000_000))

    # Annual returns: FIFA year (yr 1) + ongoing years
    # Year 1: boosted by FIFA tourism
    annual_returns = []
    ridership_base = lc_row["capacity"] * 0.92 * lc_games * (lc_transit / 100) * 1.15
    ridership = ridership_base
    for yr in range(1, 11):
        wc_bonus = ridership * 0.80 * 25 if yr == 1 else 0  # FIFA year bonus: extra 25 miles avg trip
        annual_rev = ridership * 0.80 * 12 + wc_bonus       # $0.80 × avg 12 miles/trip
        co2_val = ridership * 12 * 0.21 / 1000 * 50         # kg CO₂ → tonnes × $50/tonne
        annual_returns.append({
            "Year": f"20{'26' if yr == 1 else str(25 + yr)}",
            "Economic Return ($M)": round((annual_rev + co2_val) / 1e6, 1),
            "Phase": "FIFA 2026" if yr == 1 else "Post-Event Legacy",
        })
        ridership = ridership * 1.03

    cumulative = 0
    payback_yr = None
    for i, yr_data in enumerate(annual_returns):
        cumulative += yr_data["Economic Return ($M)"] * 1e6
        if cumulative >= base_capex and payback_yr is None:
            payback_yr = i + 1

    roi_df = pd.DataFrame(annual_returns)
    fig_roi = px.bar(
        roi_df, x="Year", y="Economic Return ($M)",
        color="Phase",
        color_discrete_map={"FIFA 2026": "#facc15", "Post-Event Legacy": "#22c55e"},
        text="Economic Return ($M)",
        template=PLOTLY_TEMPLATE,
        height=340,
    )
    fig_roi.update_traces(texttemplate="%{text:.1f}M", textposition="outside", textfont_color="white")
    fig_roi.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(gridcolor="#1e3a5f"),
        yaxis=dict(gridcolor="#1e3a5f"),
        legend=dict(orientation="h", y=-0.2),
    )
    if payback_yr:
        _pb_label = annual_returns[payback_yr - 1]["Year"]
        fig_roi.add_shape(
            type="line", xref="x", yref="paper",
            x0=_pb_label, x1=_pb_label, y0=0, y1=1,
            line=dict(color="#38bdf8", dash="dot", width=2),
        )
        fig_roi.add_annotation(
            x=_pb_label, y=1, yref="paper",
            text=f"Payback (yr {payback_yr})",
            showarrow=False, yanchor="bottom",
            font=dict(color="#38bdf8", size=11),
        )
    col_roi_left, col_roi_right = st.columns([3, 1])
    with col_roi_left:
        st.plotly_chart(fig_roi, width='stretch')
    with col_roi_right:
        st.metric("Estimated Capex", f"${base_capex/1e6:.1f}M")
        ten_yr = round(roi_df["Economic Return ($M)"].sum(), 0)
        st.metric("10-Year Return", f"${ten_yr:.0f}M")
        st.metric("Payback Period", f"{payback_yr} years" if payback_yr else ">10 years")
        st.metric("10-Year ROI", f"{round((ten_yr*1e6 / base_capex - 1)*100, 0):.0f}%")

    # ── Platform reuse framework ──────────────────────────────────────────────
    st.divider()
    st.markdown("#### Platform Reuse: Next Mega-Events")
    st.caption(
        "This mobility readiness framework is event-agnostic. "
        "The same GTFS + UHI + foot-traffic methodology applies directly to future events."
    )

    reuse_events = [
        {"Event": "Super Bowl LXI (2027)", "City": "New Orleans", "Venue Cap": "73,208",
         "Key Gap": "Suburban Superdome location; limited transit", "Platform Adaptation": "Swap GTFS feed, update climate data"},
        {"Event": "LA28 Summer Olympics (2028)", "City": "Los Angeles", "Venue Cap": "Multi-venue",
         "Key Gap": "Sprawling network; 15+ venues", "Platform Adaptation": "Multi-venue mode; modal split by event"},
        {"Event": "FIFA Women's World Cup 2027", "City": "TBD (US host)", "Venue Cap": "~60,000",
         "Key Gap": "Smaller venues, crowd management", "Platform Adaptation": "Capacity and schedule data update"},
        {"Event": "NCAA Final Four 2028", "City": "TBD", "Venue Cap": "~70,000",
         "Key Gap": "Short event window (3 days)", "Platform Adaptation": "Short-horizon demand model"},
    ]
    reuse_df = pd.DataFrame(reuse_events)
    st.dataframe(reuse_df, width='stretch', hide_index=True)

    # ── Implementation roadmap ────────────────────────────────────────────────
    st.divider()
    st.markdown("#### Implementation Roadmap")

    roadmap_data = {
        "Phase": ["Phase 1 · Immediate\n(Now → Mar 2026)", "Phase 2 · Event Operations\n(Jun–Jul 2026)", "Phase 3 · Legacy\n(Aug 2026 → )"],
        "Duration": ["9 months", "6 weeks", "Ongoing"],
        "Actions": [
            "Deploy shuttle contracts · Launch bike-share expansions · Install pedestrian shade · Publish real-time mobility API",
            "Operate dynamic shuttle frequencies · Monitor crowd density · Activate heat-risk alerts · Manage P&R lots",
            "Maintain elevated transit frequency · Convert event infrastructure to permanent use · Publish open data for city planners",
        ],
        "Implementing Partners": [
            "Transit agencies (MARTA, DART, MBTA…) · FIFA Host City Liaisons · City DOTs",
            "Event Operations teams · Transit agency dispatchers · City emergency management",
            "City planning departments · USDOT · Transit agencies · Open data portals",
        ],
        "Success Metric": [
            "Shuttle contracts signed; bike-share stations installed",
            "Transit modal split ≥ 30% per match; heat-incident rate < 0.1%",
            "Ridership 15% above pre-FIFA baseline by 2027",
        ],
    }
    roadmap_df = pd.DataFrame(roadmap_data)
    for _, phase_row in roadmap_df.iterrows():
        with st.expander(phase_row["Phase"]):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"**Actions**\n\n{phase_row['Actions']}")
            with c2:
                st.markdown(f"**Partners**\n\n{phase_row['Implementing Partners']}")
            with c3:
                st.markdown(f"**Success Metric**\n\n{phase_row['Success Metric']}")

    # ── Environmental sustainability scoreboard ───────────────────────────────
    st.divider()
    st.markdown("#### Environmental & Social Impact Scoreboard (Full Tournament)")

    total_peak_v = metrics_df["peak_visitors"].sum() * metrics_df["games"].mean()
    # If all gaps addressed: assume 25% modal shift to transit
    cars_displaced = int(total_peak_v * 0.25)
    co2_tournament = round(cars_displaced * 30 * 0.21 / 1000, 0)   # 30 km avg trip, 0.21 kg/km
    co2_value_total = round(co2_tournament * 50, 0)
    heat_risk_total = metrics_df["heat_risk_visitors"].sum()

    env_cols = st.columns(4)
    env_metrics = [
        ("Cars Displaced\n(if gaps closed)", f"{cars_displaced:,}", "per match day"),
        ("CO₂ Saved\n(full tournament)", f"{co2_tournament:,.0f} t", "tonnes CO₂"),
        ("Carbon Value", f"${co2_value_total:,.0f}", "@ $50/tonne"),
        ("Heat-Risk Visitors\nAddressed", f"{heat_risk_total:,}", "across 11 cities"),
    ]
    for col, (label, val, sub) in zip(env_cols, env_metrics):
        with col:
            st.markdown(
                f"""<div class="kpi-card">
                <div class="kpi-val" style="font-size:1.6rem">{val}</div>
                <div class="kpi-sub">{label}<br><span style="color:#4ade80">{sub}</span></div>
                </div>""",
                unsafe_allow_html=True,
            )
