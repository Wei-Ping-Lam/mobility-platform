# FIFA 2026 Host City Mobility Readiness Platform

**Rice World Cup Hackathon 2026 — Track 1: Transportation & Access**

An interactive Streamlit dashboard that predicts visitor movement, identifies first/last-mile gaps, compares transportation resilience across all 11 US FIFA 2026 host cities, and recommends data-driven transit investments.

---

## Quick Start

```bash
# From the repo root — use a dedicated venv, not your global Python.
# (pandas/numpy wheels are ABI-sensitive; a shared global interpreter with
# other unrelated packages installed can easily end up with an incompatible
# pandas/numpy pair and fail with a "binary incompatibility" ImportError.)
python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell: .venv\Scripts\Activate.ps1)
# source .venv/bin/activate     # macOS/Linux

pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
# Opens at http://localhost:8501
```

---

## Project Structure

```
Rice WC Hack/
├── dashboard/
│   ├── app.py               # Orchestrator: page config, data load, KPI header, tab dispatch
│   ├── data.py              # Shared constants, data loaders, and scoring helpers
│   ├── tabs/                # One file per tab — edit these independently
│   │   ├── tab1_overview.py
│   │   ├── tab2_demand.py
│   │   ├── tab3_gaps.py
│   │   ├── tab4_comparison.py
│   │   ├── tab5_planner.py
│   │   └── tab6_legacy.py
│   ├── requirements.txt     # Python dependencies
│   ├── README.md            # This file
│   └── cache/               # Auto-created; Parquet cache for processed data
├── store-visits-rice/       # Daily foot traffic (32 × ~210 MB .gz files)
├── urban-heat-index-rice/   # Urban heat index grid (32 × ~320 KB .gz files)
├── daily-weather-rice/      # Daily weather observations (31 × ~700 KB .gz files)
├── core-poi-geometry-rice/  # POI locations & geometry (32 × ~6 MB .gz files)
├── spend-patterns-rice/     # Consumer spend patterns (32 × ~22 MB .gz files)
├── daily-spend-brand-and-state-rice/  # Brand spend by state (32 × ~11 MB .gz files)
└── WorldCupHack_Dictionary.xlsx       # Field definitions for all datasets
```

---

## Dashboard Tabs

### 1. City Overview Map
- **Focus City** selector (local to this tab) filters the map, rankings, and radar to a single city
- Interactive US map with all 11 host cities
- Bubble **size** = number of matches hosted
- Bubble **color** = composite Mobility Readiness Score (0–100; red → yellow → green)
- Mini radar chart showing the 4-dimension score breakdown for the selected city
- City ranking list with score badges and progress bars

### 2. Visitor Demand Forecast
- Historical daily visit time series per city (sourced from store-visits data)
- 7-day rolling average overlay
- **World Cup surge projection** (June 11 – July 19, 2026):
  - Baseline × demand multiplier derived from games count
  - Shaded confidence band showing low–high surge range
- Bar chart comparing the WC demand multiplier across all cities

### 3. First/Last-Mile Gap Analysis
- **Bubble chart**: Transit Infrastructure Score (x) vs. First/Last-Mile Gap Score (y)
  - Bubble size = venue capacity; color = summer temperature
  - Quadrant overlays identify high-priority cities (weak transit + high gap)
- **Heat stress scatter**: Urban Heat Island vs. average temperature
- Ranked gap score table with color gradients (red = highest gap)

### 4. City Comparison
- **Radar chart**: All 11 cities plotted across 4 dimensions simultaneously
- **Horizontal bar chart**: Composite readiness score ranking
- **Component heatmap**: Score breakdown table for all cities and dimensions

### 5. Intervention Planner
- Select any host city and tune 4 intervention levers:
  | Lever | Description |
  |---|---|
  | Event Shuttle Frequency | Buses/hour on match days |
  | Bike-Share Stations | New docking stations within 1 mile of venue |
  | Park & Ride Capacity | Spaces served by dedicated transit |
  | Pedestrian Infrastructure | Shade, cooling stations, accessible pathways |
- Live output: updated transit score, composite score, gap score, visitors shifted to transit, and estimated CO₂ reduction per match day
- Before/after grouped bar chart
- Dynamically generated priority investment recommendations

---

## Global Controls

There is no sidebar — each tab is self-contained so teammates can work on separate tabs without touching shared UI state. Two controls remain global (in `app.py`, above the tabs) because they affect every tab's data:

| Control | Effect |
|---|---|
| **⚙️ Adjust Readiness Score Weights** (expander, collapsed by default) | Adjusts the relative contribution of each dimension to the composite score; recomputed live without reloading data |
| **Focus City** (Tab 1 only) | Filters the Overview map/rankings/radar to a single city. Other tabs always show all 11 cities and have their own independent city selectors where relevant. |

---

## Mobility Readiness Score

The composite score (0–100) is a weighted sum of four dimensions:

| Dimension | Default Weight | Source |
|---|---|---|
| Transit Infrastructure | 35% | Expert-rated transit quality (0–100) |
| Heat Safety | 20% | Derived from June–July avg temperature + humidity |
| Urban Heat Island | 15% | Mean UHI intensity from `urban-heat-index-rice` dataset |
| Venue Accessibility | 30% | Expert-rated walkability/connectivity of venue approach |

Weights are adjustable via the "⚙️ Adjust Readiness Score Weights" expander above the tabs, and normalize automatically to sum to 1.

### Heat Safety Score Formula
```
heat_index = avg_temp_c + 0.5 × max(0, humidity − 40) × (avg_temp_c / 30)
heat_score = clamp(100 − (heat_index − 20) × 2.2,  0, 100)
```

### First/Last-Mile Gap Score Formula
```
gap_score = (100 − transit_score) × (1 + max(0, avg_temp_c − 25) / 35)
```
Higher gap score = greater unmet mobility need.

---

## Data Sources & Loading Strategy

| Dataset | Fields Used | Loading Strategy |
|---|---|---|
| `store-visits-rice` | `MARKET`, `LOCAL_DATE`, `DAILY_VISITS`, `CATEGORY` | First 2 of 32 partitions, 250,000 rows each; aggregated to market × date |
| `urban-heat-index-rice` | `MARKET`, `UHI` | All 32 partitions (~10 MB total) |
| `daily-weather-rice` | Station ID, temperature, humidity, cooling degree days | All partitions; filtered to ICAO codes for host cities |
| `core-poi-geometry-rice` | `LATITUDE`, `LONGITUDE`, `NAICS_CODE`, `MARKET` | Not loaded in current version (planned) |
| `spend-patterns-rice` | `CUSTOMER_HOME_CITY`, `MARKET`, `RAW_TOTAL_SPEND` | Not loaded in current version (planned) |

### Caching
Processed DataFrames are written to `dashboard/cache/` as Parquet files on first load. Subsequent runs read from cache, making startup near-instant. Delete the `cache/` folder to force a full reload from the raw `.gz` files.

### Market Name Matching
Dataset market names (e.g. `"Dallas / Houston"`, `"Los Angeles / SF Bay Area"`) are matched to individual host cities using `.str.contains()` against a `market_key` field (e.g. `"Dallas"`, `"SF Bay"`).

---

## Host Cities Reference

| City | Venue | Capacity | Primary Transit | Transit Score |
|---|---|---|---|---|
| New York/NJ | MetLife Stadium | 82,500 | NJ Transit / Meadowlands | 95 |
| Boston | Gillette Stadium | 65,878 | MBTA Commuter Rail | 88 |
| San Francisco | Levi's Stadium | 68,500 | VTA / Caltrain | 85 |
| Philadelphia | Lincoln Financial Field | 69,796 | SEPTA Broad Street Line | 82 |
| Seattle | Lumen Field | 72,000 | Sound Transit Link | 75 |
| Atlanta | Mercedes-Benz Stadium | 71,000 | MARTA Rail | 68 |
| Los Angeles | SoFi Stadium | 70,240 | Metro C Line | 65 |
| Miami | Hard Rock Stadium | 65,326 | Metrorail + Shuttle | 55 |
| Dallas | AT&T Stadium | 80,000 | DART Light Rail | 42 |
| Houston | NRG Stadium | 72,220 | METRORail | 38 |
| Kansas City | Arrowhead Stadium | 76,416 | Limited Bus / Shuttle | 35 |

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `streamlit` | ≥ 1.35 | Web dashboard framework |
| `plotly` | ≥ 5.20 | Interactive charts and maps |
| `pandas` | ≥ 2.1 | Data loading and aggregation |
| `numpy` | ≥ 1.26 | Numerical computations |
| `pyarrow` | ≥ 14.0 | Parquet cache read/write |
| `matplotlib` | ≥ 3.8 | Required by `pandas.Styler.background_gradient` |

---

## Planned Enhancements

- **Visitor Origin Flow (Sankey)** — Parse `CUSTOMER_HOME_CITY` JSON from `spend-patterns-rice` to map where fans travel from
- **POI Density Heatmap** — Layer `core-poi-geometry-rice` onto the map to show venue-area amenity coverage
- **Full Time Series** — Load all 32 store-visit partitions for a complete 2022–2023 baseline
- **Emissions Model** — Expand CO₂ calculations to include aviation emissions from origin flow data
- **Modal Split Breakdown** — Show projected car / transit / walk / bike shares per city under each scenario
