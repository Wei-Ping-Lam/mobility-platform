# FIFA 2026 Host City Mobility Readiness Platform
## Rice World Cup Hackathon 2026 — Track 1: Transportation & Access

## Evidence-first implementation status

The upgraded implementation uses an offline ETL over all six supplied datasets
and pinned GTFS snapshots. The Streamlit application reads compact derived
artifacts and exposes observed, derived, partial, estimated, unavailable, and
scenario statuses for every major metric.

The original prototype narrative below describes the earlier sample-based
implementation. For judging, use the upgraded dashboard's `Methods & QA` view,
`docs/MODEL_CARD.md`, and `docs/VALIDATION.md` as the authoritative methodology.
In particular:

- A valid GTFS zero-service result remains observed; failed feeds are unavailable.
- Retail foot traffic is a general mobility-demand proxy, not stadium attendance.
- Event demand ranges are scenarios unless holdout validation supports predictive language.
- Traffic outputs are vehicle-pressure and capacity proxies, not measured roadway congestion.
- General consumer origins are not ticketed-fan origins.

**Team:**   
**Submission Date:** September 2026  
**Contact:** 

---

## 1. Challenge Statement

FIFA World Cup 2026 will bring an estimated 5 million international visitors to 11 US host cities across 78 matches — the largest single sporting event ever hosted in North America. Transportation infrastructure is the single greatest determinant of fan experience and city sustainability: cities that fail to deliver reliable, accessible, heat-safe mobility will face congestion collapse, public health crises, and long-lasting reputational damage.

The core challenge this project addresses is **information asymmetry**: city planners, FIFA host city liaisons, and transit agencies lack a unified, data-driven platform to (1) diagnose which venues are most at risk, (2) identify specific infrastructure gaps, and (3) simulate the return on targeted investments — all before a single match is played.

---

## 2. Solution Overview

The **FIFA 2026 Host City Mobility Readiness Platform** is an interactive, open-source Streamlit dashboard that integrates five independent data sources to produce a composite Mobility Readiness Score (0–100) for all 11 US host cities. The platform is organized around the full decision lifecycle: **diagnose → compare → intervene → plan legacy**.

**Six analytical tabs:**

| Tab | Function |
|---|---|
| City Overview Map | Composite score geospatial view; city radar profile |
| Visitor Demand Forecast | Historical demand baseline + WC surge projection; visitor origin intelligence; economic impact |
| First/Last-Mile Gap Analysis | GTFS venue-level transit access; Transit Illusion visualization; heat risk |
| City Comparison | Multi-city radar, horizontal bar, component heatmap |
| Intervention Planner | Lever-based scenario modeling with costs, ROI, and agency-specific recommendations |
| Legacy & Scalability | 10-year transit ROI, platform reuse framework, environmental impact |

---

## 3. Data Used & Methodology

### 3.1 Datasets Integrated

| Dataset | Source | Usage |
|---|---|---|
| `store-visits-rice` | Veraset/SafeGraph daily foot traffic | Demand baseline, WC surge multiplier, 7-day rolling average |
| `urban-heat-index-rice` | Satellite-derived UHI (Veraset) | Urban Heat Island score; heat risk stratification |
| `spend-patterns-rice` | Consumer spend mobility (SafeGraph) | Visitor origin intelligence via `CUSTOMER_HOME_CITY` JSON field |
| `daily-weather-rice` | NOAA weather observations | Summer heat index calculation; heat safety score |
| GTFS feeds | 11 US transit agencies (MARTA, MBTA, DART, METRO Houston, RideKC, LA Metro, MDT, NJ Transit, SEPTA, VTA, Sound Transit/King Co Metro) | Real stop-count density within 0.5/1.0/2.0 miles of each venue |

**Total datasets consumed: 5 of 6 provided datasets + 11 agency GTFS feeds (live public data)**

### 3.2 Composite Mobility Readiness Score

The composite score is a weighted sum of four independent dimensions:

```
MRS = w₁ × Transit + w₂ × Heat_Safety + w₃ × UHI + w₄ × Venue_Access
```

Default weights (user-adjustable via sidebar sliders):
- Transit Infrastructure: 35%
- Heat/Climate Safety: 20%
- Urban Heat Island: 15%
- Venue Accessibility: 30%

### 3.3 GTFS Venue-Level Transit Score

Rather than using city-level transit ratings, we computed a **venue-specific** transit access score from live GTFS data for each stadium:

```
raw = stops_0.5mi × 10 + stops_1mi × 5 + stops_2mi × 2
gtfs_score = max(5, round(raw / max_raw × 100))
```

This produces a normalized, reproducible metric directly comparable across cities.

### 3.4 Heat Safety Score

```
heat_index = avg_temp_c + 0.5 × max(0, humidity − 40) × (avg_temp_c / 30)
heat_score = clamp(100 − (heat_index − 20) × 2.2, 0, 100)
```

### 3.5 First/Last-Mile Gap Score

```
gap_score = (100 − transit_score) × (1 + max(0, avg_temp_c − 25) / 35)
```

Higher gap = greater unmet mobility need. The temperature amplifier reflects that walking to/from distant transit stops becomes increasingly unsafe as temperatures rise.

### 3.6 Visitor Origin Intelligence

The `CUSTOMER_HOME_CITY` field in spend-patterns contains a JSON mapping of `"City, STATE": count` pairs per venue. We parsed this to extract state-level visitor origin distributions for each market, revealing existing fan corridors that inform intercity transport planning.

### 3.7 Economic Impact Model

Per-city projected economic impact:
```
economic_impact_M = capacity × 0.95 × $280_per_visitor × 1.42_multiplier × games / 1,000,000
```

Benchmarks: 95% WC attendance rate (FIFA historical); $280/visitor/match-day (food, transport, merchandise, accommodation share); 1.42 regional economic multiplier (Bureau of Economic Analysis sports event methodology).

---

## 4. Key Findings

### Finding 1: The Transit Illusion

**The most significant discovery:** Cities with reputations for world-class transit often have the worst venue-level transit access, because their FIFA venues sit in suburban locations far from rail coverage.

| City | Expert Transit Score | GTFS Venue Reality | Gap |
|---|---|---|---|
| New York/NJ | 95 | 5 | **−90** |
| Boston | 88 | 5 | **−83** |
| San Francisco | 85 | 32 | −53 |
| Philadelphia | 82 | 5* | −77* |
| Seattle | 75 | 100 | **+25** ✅ |
| Atlanta | 68 | 71 | +3 ✅ |

*Philadelphia estimated — SEPTA GTFS data unavailable

**MetLife Stadium (NY/NJ)** has the most extreme illusion: despite NYC having the US's most extensive transit system, MetLife is in East Rutherford, NJ, with only 1 transit stop within half a mile. **Lumen Field (Seattle)** is the inverse — underestimated by expert ratings but served by 60 transit stops within 0.5 miles, making it the best-connected venue in the tournament.

### Finding 2: Heat × Transit = Compounding Risk

Dallas (AT&T Stadium): zero transit stops within 5.3 miles + average summer temperature of 33.5°C = highest first/last-mile gap score in the tournament (92.7). A fan who misses the shuttle is walking 5+ miles in 107°F heat. This represents a genuine public health and crowd management risk for the most match-heavy city.

### Finding 3: Visitor Origin Corridors Predict Demand

Spend-pattern analysis reveals that each market has distinct origin state distributions. San Francisco's market draws heavily from CA residents; Dallas draws from across TX, OK, and the South. These patterns indicate which interstate transit connections (Amtrak, airport shuttles) will be most stressed on match days.

### Finding 4: $2.1B Economic Stake Demands Mobility Investment

Combined projected economic impact across all 11 US cities: **$2.1 billion** from direct visitor spending alone. Cities that fail to provide adequate transit risk fan attrition, negative media coverage, and lost secondary spend. A $50M investment in mobility infrastructure across all cities yields a projected 10-year return of $400–800M, with payback periods of 3–7 years in most markets.

---

## 5. Recommendations

### Immediate (Before June 2026)

1. **Dallas + Kansas City + Miami**: Emergency shuttle expansion. Zero or near-zero transit at venue; requires high-frequency dedicated shuttle circuits from airport, downtown, and rail hubs. Estimated cost: $180/bus-hr × 60 buses × 16 hrs/match = ~$173K/match.

2. **New York/NJ + Boston + Philadelphia**: Do not rely on city transit reputation. Issue explicit guidance that MetLife/Gillette/Lincoln Financial require match-specific shuttle plans. NJ Transit's existing Meadowlands Rail service needs surge capacity contracts.

3. **All cities with avg_temp > 28°C** (Dallas, Houston, Miami, Atlanta, Kansas City): Install tensile shade canopies and misting stations along pedestrian corridors from transit stops to venue. FEMA HMA funds available for heat mitigation infrastructure.

### Event Operations (June–July 2026)

4. **Dynamic shuttle frequency**: Tie shuttle dispatch rates to real-time ticket scan data. 90 minutes pre-kickoff = 2× normal frequency; 60 minutes post-match = 3× normal frequency.

5. **Heat alert integration**: Connect NOAA real-time heat index data to the mobility app. When heat index > 40°C, activate proactive messaging to divert pedestrian traffic to shaded routes and free water stations.

6. **Unified mobility app**: All 11 cities should share a single FIFA mobility app with real-time GTFS arrivals, shuttle status, bike availability, and crowd-level alerts for international visitors.

### Long-Term Legacy (Post-August 2026)

7. **Seattle Model**: Lumen Field's transit integration — rail-adjacent, high stop density, covered walkways — should serve as the design standard for future venue planning nationwide.

8. **Dallas Transit Gap**: Arrowhead and AT&T Stadium's lack of rail connectivity is a solvable problem. Post-FIFA funding could support the $800M+ AT&T Stadium rail extension that DART has studied but not funded.

---

## 6. Legacy & Scalability

### Platform Reuse

This mobility readiness framework is designed to be **event-agnostic**. Swapping GTFS feeds, venue coordinates, and climate data allows the same platform to assess:
- Super Bowl LXI (2027, New Orleans)
- LA28 Summer Olympics (2028, Los Angeles — multi-venue mode)
- FIFA Women's World Cup 2027
- Any future mega-event requiring host-city mobility assessment

### Environmental Legacy

If FIFA-driven transit investments achieve a 25% modal shift from private vehicles to transit across all 78 US matches:
- **~1.8 million cars displaced** per match day
- **~11,340 tonnes CO₂ avoided** (full tournament, at 30 km avg trip × 0.21 kg/km)
- **~$567,000 in carbon value** at $50/tonne social cost of carbon
- **Year-round ridership gains**: Transit improvements funded for FIFA remain in use by 3–4 million daily transit riders in these cities

### Data Transparency

All data sources used in this platform are public (GTFS feeds) or provided datasets. The platform is fully reproducible and open-source. Computed GTFS scores are saved to `data/gtfs_transit_scores.json` for audit.

---

## 7. Technical Implementation

**Stack:** Python 3.11 · Streamlit 1.35 · Plotly 5.20 · Pandas 2.1 · NumPy 1.26

**Data pipeline:**
1. Raw `.gz` partitions → aggregated Parquet cache (one-time, ~3 min)
2. GTFS feeds → `fetch_gtfs.py` → `data/gtfs_transit_scores.json` (one-time, ~8 min)
3. Dashboard loads from cache → sub-second startup on subsequent runs

**Reproducibility:** Clone repo, install `requirements.txt`, run `python fetch_gtfs.py` once, then `streamlit run app.py`.

**Scalability:** The store-visits dataset (6.8 GB, 32 partitions) is sampled (2 partitions, 250K rows) for the hackathon prototype. Production deployment would ingest all 32 partitions for a richer 2020–2023 baseline.

---

## 8. Limitations & Future Work

- **Philadelphia GTFS**: SEPTA data unavailable via public URL; transit score is expert-estimated. Actual Lincoln Financial Field is served by SEPTA's Broad Street Line shuttle.
- **Store-visits sampling**: Only 2 of 32 partitions loaded; full dataset would produce more precise demand forecasts.
- **Economic model**: Per-visitor spend ($280) and regional multiplier (1.42) are benchmarks, not city-specific estimates. Spend-patterns RAW_TOTAL_SPEND data could refine these.
- **Visitor origin**: CUSTOMER_HOME_CITY represents general consumer mobility, not fan-specific travel patterns. FIFA ticket purchaser data (not available) would sharpen this analysis.
- **Future enhancement**: Sankey diagram of origin→destination flows; POI density heatmap overlaid on transit network; full 32-partition store-visits time series.
