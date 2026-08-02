# Data Documentation
## Rice World Cup Cities Hack — Dataset Reference

---

## Important Disclaimer

> All datasets are **sample and transformed data for educational/hackathon use only.**
> The following transformations have been applied by the data provider:
> - **Multiplicative noise** applied to magnitude fields (spending amounts, visit counts, transaction counts)
> - **Additive noise** applied to fixed-scale variables (temperatures)
> - **Spatial jittering** applied to latitude/longitude coordinates
>
> Outputs derived from these datasets should be treated as **methodology demonstrations**, not real-world assessments.

---

## Current platform contract

The shared interface version is `0.3.0`. It defines `SourceReference`,
`MatchEvent`, `MovementScenario`, `AccessGapResult`, `InterventionPackage`,
`InterventionOutcome`, and `InvestmentRecommendation`. Those definitions are
release interfaces, not proof that supplemental sources or transportation
results have been integrated. Current and target behavior are separated in
`docs/VALIDATION.md`.

The canonical supplied-data root is the repository-local `Rice WC Hack/`
directory. It contains all six datasets below, remains read-only and untracked,
and is the source named in derived metric provenance. GTFS is a separate,
supplemental source and must not be described as part of the Rice collection.

The live dashboard does not scan these files at startup. The offline ETL reads
them in bounded chunks, validates partitions, keys, dates, coordinates, ranges,
nulls, and known sentinels, and writes compact Parquet artifacts plus
`dashboard/cache/manifest.json` and `dashboard/cache/qa_report.json`. The
manifest records raw-to-derived row counts, coverage warnings, artifact hashes,
and quality checks. Combined source markets are allocated only through the
explicit mappings in `dashboard/mobility_platform/mappings.py` and retain a
partial-evidence warning.

The current full-data audit found all expected partitions except the documented
`daily-weather-rice_2_0_0.csv.gz`. It also found two valid
`CUSTOMER_HOME_CITY` JSON representations; the ETL supports and tests both.
The run-specific row counts and hashes in `dashboard/cache/manifest.json` are
authoritative over the approximate inventory figures below.

The source data are noisy educational data. Store visits and commercial spend
are mobility/economic proxies, not stadium attendance or ticketed-fan behavior.

## Supplemental release evidence

FIFA schedule, agency GTFS, OpenStreetMap networks, and EPA/FTA/FHWA factor
references are not part of the Rice collection. They are eligible only after an
offline pipeline records publisher, URL, retrieval time, version, license,
coverage, evidence status, and SHA-256. Their intended uses and current
integration status are listed in `docs/SOURCE_REGISTER.md`.

- FIFA supplies match context, not attendance observations.
- GTFS supplies scheduled service, not delivered service, ridership, crowding,
  or reliability.
- OSM supports network planning; missing tags stay unknown and do not establish
  accessibility or route safety.
- EPA/FTA/FHWA inputs are planning factors and conceptual costs, not local
  inventories, engineering estimates, or bids.

## Overview

| Dataset | Files | Compressed Size | Records (est.) | Date Range | Granularity |
|---|---|---|---|---|---|
| `store-visits-rice` | 32 × .csv.gz | 6.8 GB | 223,342,163 rows | 2020–2024 daily | Store × Day |
| `spend-patterns-rice` | 32 × .csv.gz | 719 MB | 1,026,618 rows | 2019–2024 monthly | Location × Month |
| `daily-spend-brand-and-state-rice` | 32 × .csv.gz | 341 MB | ~20 M rows | 2020–2024 daily | Brand × State × Day |
| `core-poi-geometry-rice` | 32 × .csv.gz | 189 MB | ~520 K rows | — | Location (static) |
| `daily-weather-rice` | 31 × .csv.gz | 22 MB | ~730 K rows | 2020–2024 daily | Station × Day |
| `urban-heat-index-rice` | 32 × .csv.gz | 10 MB | ~1.25 M rows | — | Grid Point (static) |

**Data Dictionary:** `WorldCupHack_Dictionary.xlsx` (sheets: *Read Me*, *Data Variables*)

---

## File Partitioning Scheme

All datasets are partitioned using a 4 × 8 grid:

```
[dataset-name]_[row]_[col]_0.csv.gz
  row: 0, 1, 2, 3
  col: 0, 1, 2, 3, 4, 5, 6, 7
```

Partitions represent geographic subdivisions of the dataset (likely lat/lon tiles). Load multiple files and concatenate to increase coverage. The `daily-weather-rice` dataset is missing partition `2_0_0` (31 files instead of 32).

---

## Geographic Markets

All datasets are scoped to the **11 FIFA 2026 US host city markets**. Note: market names are not consistent across datasets.

| City | `store-visits-rice` Market | `urban-heat-index-rice` / `core-poi-geometry-rice` Market |
|---|---|---|
| Atlanta | `Atlanta` | `Atlanta` |
| Boston | `Boston` | `Boston` |
| Dallas | `Dallas / Houston` | `Dallas` |
| Houston | `Dallas / Houston` | `Houston` |
| Kansas City | `Kansas City` | `Kansas City` |
| Los Angeles | `Los Angeles / SF Bay Area` | `Los Angeles` |
| San Francisco | `Los Angeles / SF Bay Area` | `San Francisco Bay Area` |
| Miami | `Miami` | `Miami` |
| New York/NJ | `New York/New Jersey` | `New York/New Jersey` |
| Philadelphia | `Philadelphia` | `Philadelphia` |
| Seattle | `Seattle` | `Seattle` |

**Note:** `store-visits-rice` combines Dallas + Houston into one market, and Los Angeles + San Francisco into one. All other datasets split them individually.

---

---

## Dataset 1: `store-visits-rice`

**What it is:** Daily foot-traffic visit counts for retail and commercial locations across all 11 host city markets. The primary signal for measuring visitor demand, economic activity, and mobility patterns.

**Grain:** One row = one store on one day.

**Date range:** 2020-01-01 to 2024-12-31 (1,827 unique dates)

**File sample:** `store-visits-rice_0_0_0.csv.gz` contains Miami market only; other partitions contain other markets.

### Fields

| Field | Type | Null % | Unique | Range / Notes |
|---|---|---|---|---|
| `STORE_ID` | string | 0% | ~147,832 | UUID identifying a unique physical store location |
| `NAME` | string | 0% | ~10,602 | Store display name (e.g., `"Burger King"`) |
| `BRAND` | string | 0% | ~5,015 | Brand name; may differ from NAME for franchise locations |
| `STATE` | string | 0% | 11 | Two-letter state abbreviation (CA, FL, GA, KS, MA, MO, NJ, NY, PA, TX, WA) |
| `MARKET` | string | 0% | 9 | Metro market label — see market mapping table above |
| `NAICS_CODE` | int | 0% | 264 | North American Industry Classification System code (6-digit) |
| `CATEGORY` | string | 0% | 132 | NAICS category label (e.g., `"Restaurants and Other Eating Places"`) |
| `SUB_CATEGORY` | string | 0% | 246 | NAICS sub-category label (e.g., `"Limited-Service Restaurants"`) |
| `LOCAL_DATE` | string (YYYY-MM-DD) | 0% | 1,827 | Date of the visit count observation |
| `DAILY_VISITS` | int | 0% | ~24,832 | Number of device pings attributed to a store visit on this date. Range: 0–441,377. Mean ≈ 838 |
| `STOCK_EXCHANGE` | string | 49% | 28 | Exchange listing (NYSE, NASDAQ, etc.) — only for publicly traded brands |
| `STOCK_SYMBOL` | string | 49% | 593 | Ticker symbol — only for publicly traded brands |
| `VERSION_ID` | float | 0% | 1 | Data version identifier (value = 9.0 in current dataset) |

### Usage Notes
- `DAILY_VISITS` has noise applied; use for relative comparisons, not absolute counts.
- Filter by `NAICS_CODE` to isolate specific industries (e.g., 722513 = Limited-Service Restaurants; 721110 = Hotels).
- Aggregate by `MARKET` + `LOCAL_DATE` to get city-level daily visit volume.
- The dataset spans 5 years of daily data, enabling year-over-year and seasonal analysis.

---

## Dataset 2: `spend-patterns-rice`

**What it is:** Monthly consumer spending analytics at the individual location level. Covers spending amounts, customer demographics (income buckets, visit frequency), where customers come from, and related service usage. The richest behavioral dataset in the collection.

**Grain:** One row = one location for one calendar month.

**Date range:** 2019-12-01 to 2024-12-01 (monthly; 61 unique periods)

### Fields

#### Identity & Location

| Field | Type | Null % | Unique | Notes |
|---|---|---|---|---|
| `PLACEKEY` | string | 0% | ~52,223 | Unique place identifier (links to `core-poi-geometry-rice`) |
| `PARENT_PLACEKEY` | string | 75% | ~9,872 | Parent location (e.g., mall containing this store); often null |
| `LOCATION_NAME` | string | 0% | ~42,699 | Store/location display name |
| `BRANDS` | string | 54% | ~3,530 | Brand name; null for independent businesses |
| `STREET_ADDRESS` | string | 0% | ~50,917 | Full street address |
| `CITY` | string | 0% | 63 | City name |
| `REGION` | string | 0% | 47 | State abbreviation |
| `POSTAL_CODE` | int | 0% | 1,265 | ZIP code |
| `MARKET` | string | 0% | 11 | Metro market label (uses split naming — 11 distinct cities) |
| `ISO_COUNTRY_CODE` | string | 0% | 1 | Always `"US"` |
| `LATITUDE` | float | 0% | ~74,097 | Jittered latitude |
| `LONGITUDE` | float | 0% | ~74,361 | Jittered longitude |
| `NAICS_CODE` | int | 0% | 513 | Industry classification |
| `TOP_CATEGORY` | string | 0% | 221 | NAICS top-level category label |
| `SUB_CATEGORY` | string | 6% | 362 | NAICS sub-category label |

#### Spending Metrics

| Field | Type | Null % | Notes |
|---|---|---|---|
| `SPEND_DATE_RANGE_START` | timestamp | 0% | First day of the reporting month |
| `SPEND_DATE_RANGE_END` | timestamp | 0% | First day of the following month |
| `RAW_TOTAL_SPEND` | float | 0% | Total consumer spend at this location during the month (noise applied) |
| `RAW_NUM_CUSTOMERS` | float | 0% | Estimated unique customers (noise applied) |
| `RAW_NUM_TRANSACTIONS` | float | 0% | Estimated total transactions (noise applied) |
| `MEDIAN_SPEND_PER_CUSTOMER` | float | 0% | Median total spend per unique customer during the month |
| `MEDIAN_SPEND_PER_TRANSACTION` | float | 0% | Median spend per individual transaction |
| `ONLINE_SPEND` | float | 0% | Portion of spend attributed to online/card-not-present transactions |
| `ONLINE_TRANSACTIONS` | float | 0% | Count of online transactions |
| `SPEND_PCT_CHANGE_VS_PREV_MONTH` | int | 15% | Month-over-month spend change (%) |
| `SPEND_PCT_CHANGE_VS_PREV_YEAR` | int | 26% | Year-over-year spend change (%) |

#### JSON-Encoded Behavioral Fields

These fields are stored as **JSON strings** and must be parsed with `json.loads()`:

| Field | Structure | Description |
|---|---|---|
| `CUSTOMER_HOME_CITY` | `{"City, ST": count, ...}` | Distribution of where customers live. Keys are `"City, ST"` strings; values are estimated customer counts from that origin. Powerful for visitor origin-flow analysis. |
| `SPEND_BY_DAY` | `[float, float, ...]` | Array of daily spend totals across the reporting month (one value per calendar day, length = days in month). |
| `SPEND_BY_DAY_OF_WEEK` | `{"Mon": float, "Tue": float, ...}` | Spend aggregated by day of week. |
| `SPEND_PER_TRANSACTION_BY_DAY` | `[float, float, ...]` | Average spend per transaction for each calendar day. |
| `SPEND_PER_TRANSACTION_PERCENTILES` | `{"p10": float, "p25": float, ...}` | Spend distribution percentiles per transaction. |
| `SPEND_BY_TRANSACTION_INTERMEDIARY` | `{"card": float, "cash": float, ...}` | Spend breakdown by payment method. |
| `TRANSACTION_INTERMEDIARY` | JSON dict | Transaction count breakdown by payment method. |
| `BUCKETED_CUSTOMER_INCOMES` | JSON dict | Customer count by income bracket (e.g., `"$0-50k"`, `"$50-100k"`, etc.). |
| `BUCKETED_CUSTOMER_FREQUENCY` | JSON dict | Customers binned by visit frequency (once, 2–4×, 5+×, etc.). |
| `MEAN_SPEND_PER_CUSTOMER_BY_INCOME` | JSON dict | Average spend per customer, segmented by income bracket. |
| `MEAN_SPEND_PER_CUSTOMER_BY_FREQUENCY` | JSON dict | Average spend per customer, segmented by visit frequency. |
| `DAY_COUNTS` | JSON dict | Number of days each weekday appeared in the reporting period. |

#### Related Services (% of customers)

These fields give the fraction of this location's customers who also used each service:

| Field | Description |
|---|---|
| `RELATED_RIDESHARE_SERVICE_PCT` | % customers who used Uber/Lyft in the period — useful for first/last-mile inference |
| `RELATED_DELIVERY_SERVICE_PCT` | % who used delivery services (DoorDash, UberEats, etc.) |
| `RELATED_BUYNOWPAYLATER_SERVICE_PCT` | % who used BNPL (Afterpay, Klarna, etc.) |
| `RELATED_PAYMENT_PLATFORM_PCT` | % who used digital payment platforms (PayPal, Venmo, etc.) |
| `RELATED_STREAMING_CABLE_PCT` | % who pay for streaming/cable subscriptions |
| `RELATED_WIRELESS_CARRIER_PCT` | % associated with specific wireless carriers |
| `RELATED_CROSS_SHOPPING_PHYSICAL_BRANDS_PCT` | % who shopped other physical-store brands during the period |
| `RELATED_CROSS_SHOPPING_ONLINE_MERCHANTS_PCT` | % who also shopped online merchants |
| `RELATED_CROSS_SHOPPING_LOCAL_BRANDS_PCT` | % who also shopped local/independent businesses |
| `RELATED_CROSS_SHOPPING_SAME_CATEGORY_BRANDS_PCT` | % who shopped competitors in the same category |

### Usage Notes
- Parse JSON fields with `json.loads(row['CUSTOMER_HOME_CITY'])` before analysis.
- `RELATED_RIDESHARE_SERVICE_PCT` is a direct signal for first/last-mile demand at a location.
- `CUSTOMER_HOME_CITY` enables Sankey/flow diagrams of visitor origins by host city.
- Join to `core-poi-geometry-rice` on `PLACEKEY` to add polygon geometry.

---

## Dataset 3: `daily-spend-brand-and-state-rice`

**What it is:** Daily spending totals aggregated at the brand × state level. Lighter and faster to load than `spend-patterns-rice`; useful for brand-level trend analysis and state-level economic activity monitoring.

**Grain:** One row = one brand in one state on one day.

**Date range:** 2020-01-01 to 2024-12-31

### Fields

| Field | Type | Null % | Notes |
|---|---|---|---|
| `BRAND_ID` | int | 0% | Numeric brand identifier |
| `BRAND_NAME` | string | 0% | ~11,698 unique brand names |
| `MARKET` | string | 0% | Metro market label |
| `STATE_ABBR` | string | 0% | Two-letter state code (11 states: CA FL GA KS MA MO NJ NY PA TX WA) |
| `TRANS_DATE` | string (YYYY-MM-DD) | 0% | Transaction date |
| `SPEND_AMOUNT` | float | 0% | Total spend for this brand in this state on this date (noise applied) |
| `TRANS_COUNT` | float | 0% | Estimated transaction count (noise applied) |
| `VERSION` | string (YYYY-MM-DD) | 0% | Dataset version date (e.g., `2026-06-21`) |

### Usage Notes
- Best for comparing brand-level spending trajectories across cities.
- Combine with `store-visits-rice` to compute spend-per-visit ratios.
- `TRANS_COUNT` can be used to derive average transaction size: `SPEND_AMOUNT / TRANS_COUNT`.

---

## Dataset 4: `core-poi-geometry-rice`

**What it is:** Master reference table for all Points of Interest (POI) — physical locations with full geographic detail including polygon footprints, operating hours, NAICS classification, and metadata. The spatial backbone of the dataset collection.

**Grain:** One row = one physical location (static; no time dimension).

**Total locations:** ~520,000 unique places across all 11 markets.

### Fields

#### Identity

| Field | Type | Null % | Unique | Notes |
|---|---|---|---|---|
| `PLACEKEY` | string | 0% | ~508,942 | Primary unique identifier — use to join with `spend-patterns-rice` |
| `SAFEGRAPH_PLACE_ID` | string | — | — | Legacy identifier (not in data dictionary; present in files) |
| `PARENT_PLACEKEY` | string | 68% | ~38,950 | Parent location ID (e.g., the mall containing this store) |
| `STORE_ID` | string | 93% | ~30,314 | Chain store identifier; only populated for major chains (7%) |
| `LOCATION_NAME` | string | 0% | ~465,644 | Display name of the location |
| `BRANDS` | string | 0% | ~4,261 | Associated brand name |

#### Classification

| Field | Type | Null % | Unique | Notes |
|---|---|---|---|---|
| `NAICS_CODE` | int | 0% | 1,141 | Primary NAICS code |
| `NAICS_CODE_2022` | int | 0% | 1,109 | Updated 2022 NAICS code |
| `TOP_CATEGORY` | string | 0% | 331 | NAICS top-level category (e.g., `"Grocery Stores"`) |
| `TOP_CATEGORY_2022` | string | 0% | 329 | Updated 2022 top-level category |
| `SUB_CATEGORY` | string | 7% | 834 | NAICS sub-category |
| `SUB_CATEGORY_2022` | string | 7% | 805 | Updated 2022 sub-category |
| `CATEGORY_TAGS` | string (JSON) | 0% | ~33,373 | Additional free-form category tags |

#### Location

| Field | Type | Null % | Notes |
|---|---|---|---|
| `STREET_ADDRESS` | string | 0% | Full street address |
| `CITY` | string | 0% | City name (63 unique cities across 11 markets) |
| `REGION` | string | 0% | State abbreviation (163 unique values including territories) |
| `POSTAL_CODE` | int | 0% | ZIP code (~5,170 unique) |
| `MARKET` | string | 0% | Metro market label (11 unique — uses split naming) |
| `ISO_COUNTRY_CODE` | string | 0% | Country code (mostly `"US"`; includes some international) |
| `LATITUDE` | float | 0% | Spatially jittered latitude |
| `LONGITUDE` | float | 0% | Spatially jittered longitude |

#### Geometry

| Field | Type | Null % | Notes |
|---|---|---|---|
| `GEOMETRY_TYPE` | string | 0% | `"POLYGON"` or `"POINT"` |
| `POLYGON_WKT` | string | 6% | Well-Known Text polygon boundary of the location footprint |
| `POLYGON_CLASS` | string | 17% | Polygon quality class |
| `WKT_AREA_SQ_METERS` | float | 6% | Footprint area in square meters. Range: 0–35,313,567 |
| `ENCLOSED` | bool | 6% | Whether the location is inside an enclosed structure (e.g., a mall) |
| `INCLUDES_PARKING_LOT` | bool | 8% | Whether the polygon includes adjacent parking |
| `IS_SYNTHETIC` | bool | 6% | Whether the polygon was computationally estimated vs. surveyed |

#### Operating Information

| Field | Type | Null % | Notes |
|---|---|---|---|
| `OPEN_HOURS` | string (JSON) | 63% | JSON dict of operating hours by day: `{"Mon": [["9:00","17:00"]], ...}`. Only 37% populated. |
| `OPENED_ON` | date | 99% | Date the location opened (very sparse) |
| `CLOSED_ON` | date | 89% | Date the location closed (if applicable) |
| `TRACKING_CLOSED_SINCE` | date | 3% | Date tracking coverage began |
| `PHONE_NUMBER` | string | <1% | Phone number (nearly empty) |
| `WEBSITE` | string | 79% | Website URL |
| `DOMAINS` | string (JSON) | 0% | Associated web domains |

### Usage Notes
- Join to `spend-patterns-rice` on `PLACEKEY` to add geometry to spend data.
- Filter `TOP_CATEGORY == "Urban Transit Systems"` (NAICS 485) to identify transit POIs.
- `WKT_AREA_SQ_METERS` enables venue size analysis (large areas = stadiums, malls, transit hubs).
- `ENCLOSED = True` + `INCLUDES_PARKING_LOT = True` identifies venues that are car-dependent.
- Parse `OPEN_HOURS` with `json.loads()` to analyze operating hours patterns.

---

## Dataset 5: `daily-weather-rice`

**What it is:** Daily meteorological observations from 401 weather stations, covering the full 11-market region. Used for climate comfort scoring, heat risk assessment, and understanding how weather affects visitor mobility.

**Grain:** One row = one weather station on one day.

**Date range:** 2020-01-01 to 2024-12-31 (1,827 unique dates)

**Station count:** 401 ICAO/FAA station identifiers (ICAO K-prefix format, e.g., `KATL`, `KMIA`)

### Fields

> **Note:** All column names in this dataset are extremely verbose (include full measurement descriptions and units). The table below shows the short alias used in the dashboard alongside the raw column name.

| Short Name | Raw Column Name | Type | Range | Notes |
|---|---|---|---|---|
| `station` | `CITY_LOCATION_IDENTIFIER__UP_TO_9_ALPHANUMERIC_CHARACTERS_` | string | — | ICAO station ID (e.g., `KATL` = Atlanta Hartsfield) |
| `date` | `VALID_DATE_AS_YYYYMMDD` | string (YYYYMMDD) | 2020–2024 | Observation date |
| `avg_temp_c` | `AVERAGE_TEMPERATURE_C___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE` | float | −40.5 to +47.6 °C | Daily mean temperature. Noise applied. |
| `max_temp_c` | `MAXIMUM_TEMPERATURE_C___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE` | float | −40.4 to +57.9 °C | Daily maximum temperature |
| `min_temp_c` | `MINIMUM_TEMPERATURE_C___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE` | float | −43.5 to +48.3 °C | Daily minimum temperature |
| `humidity` | `AVERAGE_RELATIVE_HUMIDITY_____FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE` | float | 0.8 – 100.0 % | Daily mean relative humidity |
| `wind_knots` | `AVERAGE_WIND_SPEED_KNOTS___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE` | float | 0 – 90.2 kts | Daily mean wind speed |
| `visibility_km` | `AVERAGE_VISIBILITY_KILOMETERS___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE` | float | 0 – 217.7 km | Daily mean visibility |
| `precip` | `PRECIPITATION_INTEGER_IN_HUNDREDTHS_OF_A_MILLIMETER___LIQUID_EQUIVALENT____0__IS_USED_FOR_TRACE_AMOUNTS_AND___1__IS_USED_FOR_NO_PRECIPITATION` | int | −1 to 59,127 (hundredths mm) | −1 = no precipitation; 0 = trace amounts; divide by 100 for mm |
| `dew_point_f` | `AVERAGE_DEW_POINT_F___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE` | float | — °F | Daily dew point in Fahrenheit. Note: sentinel value −999998.5 indicates missing. |
| `sea_level_pressure` | `AVERAGE_SEA_LEVEL_PRESSURE_MILLIBARS___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE` | float | — mb | Sentinel value −999999 indicates missing. |
| `heating_dd` | `HEATING_DEGREE_DAYS_C___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE` | float | 0 – 61.2 | Heating degree days (base 18°C) |
| `cooling_dd` | `COOLING_DEGREE_DAYS_C___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE` | int | 0 – 30.2 | Cooling degree days (base 18°C) — proxy for air conditioning / energy demand |

### FIFA Host City Station Codes

| City | ICAO Code |
|---|---|
| Atlanta | `KATL` |
| Boston | `KBOS` |
| Dallas | `KDFW` |
| Houston | `KHOU` |
| Kansas City | `KMCI` |
| Los Angeles | `KLAX` |
| Miami | `KMIA` |
| New York/NJ | `KJFK` |
| Philadelphia | `KPHL` |
| San Francisco | `KSFO` |
| Seattle | `KSEA` |

### Usage Notes
- Filter by ICAO code to extract data for a specific host city.
- `COOLING_DEGREE_DAYS` is a direct proxy for summer energy demand (air conditioning load).
- To convert precipitation: divide the integer value by 100 to get millimeters. −1 = no precip day.
- Sentinel values (−999998.5 for dew point; −999999 for pressure) indicate missing measurements — filter these out before analysis.
- Summer (June–July) `avg_temp_c` + `humidity` can be combined into a **Heat Index** to assess pedestrian comfort and walkability.

---

## Dataset 6: `urban-heat-index-rice`

**What it is:** A gridded dataset of Urban Heat Island (UHI) intensity values across all 11 host city markets. Each row is a geographic point with a UHI value representing how much hotter that point is compared to surrounding rural areas. Critical for identifying zones where outdoor mobility is heat-stressed.

**Grain:** One row = one geographic grid point (static; no time dimension).

**Total points:** ~1,244,891 unique geographic points

### Fields

| Field | Type | Null % | Range | Notes |
|---|---|---|---|---|
| `LATITUDE` | float | 0% | 18.215 – 61.635 | Jittered latitude of the grid point |
| `LONGITUDE` | float | 0% | −149.815 – −66.075 | Jittered longitude of the grid point |
| `MARKET` | string | 0% | 11 unique | City market label (split naming — 11 distinct cities) |
| `POINT_GEOMETRY` | string | 0% | ~1,244,891 unique | WKB hex-encoded point geometry (parse with `shapely.wkb.loads(bytes.fromhex(val))` if needed) |
| `UHI` | int | 0% | 1 – 11 | Urban Heat Island intensity in degrees Celsius above rural surroundings. Higher = hotter urban microclimate. |

### UHI Value Distribution (all markets combined)

| Statistic | Value |
|---|---|
| Mean | 5.31 °C |
| Std Dev | 3.40 °C |
| 25th percentile | 2 °C |
| Median | 5 °C |
| 75th percentile | 9 °C |
| Maximum | 11 °C |

### Usage Notes
- Aggregate by `MARKET` to compute a city-level mean/max UHI score.
- Overlay high-UHI grid points (UHI ≥ 8) with `core-poi-geometry-rice` locations to identify venues in heat-stressed zones.
- Combine with `daily-weather-rice` summer temperatures: `effective_temp = avg_temp_c + avg_uhi` gives a local perceived temperature.
- The full dataset (~10 MB compressed) can be loaded entirely into memory — no chunking needed.
- `POINT_GEOMETRY` is in WKB hex format; for most analyses, `LATITUDE`/`LONGITUDE` are sufficient.

---

## Cross-Dataset Relationships

```
core-poi-geometry-rice  ──── PLACEKEY ────►  spend-patterns-rice
                         ◄─── PLACEKEY ─────  (join for geometry + spend)

store-visits-rice ────── STORE_ID ──────────► core-poi-geometry-rice
                  ────── BRAND / NAME ───────► daily-spend-brand-and-state-rice

urban-heat-index-rice ── MARKET + lat/lon ──► core-poi-geometry-rice
                                              (spatial join for UHI at each POI)

daily-weather-rice ───── MARKET (via ICAO) ─► all datasets
                         (time-join on date for weather context)

daily-spend-brand-and-state-rice ─ BRAND ──► store-visits-rice
                                 ─ STATE ───► core-poi-geometry-rice REGION
```

---

## Common Analysis Patterns

### Load and aggregate store visits by city and date
```python
import pandas as pd, glob

files = sorted(glob.glob("store-visits-rice/*.gz"))[:4]  # adjust slice for coverage
chunks = []
for f in files:
    df = pd.read_csv(f, usecols=["MARKET", "LOCAL_DATE", "DAILY_VISITS"], nrows=250_000)
    chunks.append(df)

daily = pd.concat(chunks).groupby(["MARKET", "LOCAL_DATE"])["DAILY_VISITS"].sum().reset_index()
```

### Parse CUSTOMER_HOME_CITY to build origin flows
```python
import pandas as pd, json

df = pd.read_csv("spend-patterns-rice/spend-patterns-rice_0_0_0.csv.gz",
                 usecols=["MARKET", "CUSTOMER_HOME_CITY", "RAW_TOTAL_SPEND"], nrows=10_000)

rows = []
for _, r in df.iterrows():
    try:
        origins = json.loads(r["CUSTOMER_HOME_CITY"].replace("'", '"'))
        for city, count in origins.items():
            rows.append({"destination": r["MARKET"], "origin": city, "count": count})
    except Exception:
        continue

flows = pd.DataFrame(rows)
```

### Load all UHI data (small enough to fully load)
```python
import pandas as pd, glob

uhi = pd.concat([pd.read_csv(f) for f in glob.glob("urban-heat-index-rice/*.gz")])
city_uhi = uhi.groupby("MARKET")["UHI"].agg(["mean", "max"]).reset_index()
```

### Filter weather for a specific host city station
```python
import pandas as pd, glob

TARGET_STATION = "KATL"  # Atlanta
dfs = []
for f in glob.glob("daily-weather-rice/*.gz"):
    df = pd.read_csv(f)
    station_col = [c for c in df.columns if "CITY_LOCATION" in c][0]
    dfs.append(df[df[station_col] == TARGET_STATION])

weather = pd.concat(dfs)
```
