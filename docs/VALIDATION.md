# Validation and release gates

## Data validation

- All six dataset directories are required for a full ETL run.
- `Rice WC Hack/` is the canonical local source root. Raw files remain read-only
  and untracked; generated artifacts identify the source collection and exact
  dataset in their manifests and metric evidence.
- The expected 4 x 8 partition grid is enumerated. The supplied missing
  `daily-weather-rice_2_0_0.csv.gz` partition is surfaced as partial coverage.
- Because that partition removes most documented primary host stations, the
  ETL selects the nearest station actually present in the Rice files and records
  its identifier and venue distance. Miami (34.0 mi) and New York/New Jersey
  (50.9 mi) remain partial under the 30-mile rule. Station identity and location
  were checked against the official NOAA ISD station history metadata:
  <https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv>.
- Required columns, duplicate keys, dates, numeric ranges, coordinates, nulls,
  canonical market labels, and known weather sentinels are recorded per input
  chunk without retaining raw rows.
- Raw-to-derived row counts, coverage warnings, generation times, and SHA-256
  artifact hashes are written to `manifest.json` and `qa_report.json`.
- Combined source markets are tested against exact mappings; substring matching
  is prohibited.
- Both customer-origin JSON schemas present in `spend-patterns-rice` are tested:
  direct location/count mappings and `key_value` lists. Valid alternate-schema
  rows must not be reported as rejected values.
- GTFS feeds record content hashes, required-file status, valid calendar span,
  event-window departures, stop/route counts, venue coordinates, and
  observed/partial/unavailable status.

## Model validation

- Readiness values stay within 0-100 and weights normalize to one.
- Transit improvements cannot reduce readiness.
- Higher heat or UHI cannot improve the corresponding safety score.
- Zero-intervention scenarios produce zero shifted trips, vehicle-km, and
  emissions avoided.
- Scenario costs, capacities, vehicle-km, and emissions are nonnegative.
- A valid zero-service GTFS result remains observed zero; unavailable feeds have
  no score and no expert fallback.
- The demand baseline uses rolling 2023 and 2024 holdouts and reports MAE,
  RMSE, WAPE, and comparison with a 364-day seasonal-naive comparator.
- If the baseline does not consistently beat that comparator, the UI uses
  scenario language rather than validated-prediction language.
- Partial MRS values remain visible but have `rankable=false` until every
  non-zero-weight core component is evidence-eligible.
- The default supplied-data profile has zero transit weight and is explicitly
  labeled as a Rice evidence lens, not a complete transit-readiness result.

## UI validation

- Cache-only startup works without raw-data scans; full-data startup works after
  the offline ETL.
- Missing data produces an actionable warning and remains visible in tables.
- Evidence status is visible on every headline metric and important charts have
  table equivalents.
- Scenario downloads serialize the displayed assumptions and outputs.
- Executive, Explorer, and Methods & QA views are designed for desktop and
  narrow layouts.
- Gray incomplete venues remain on the map without being assigned a readiness
  color.

## Automated checks

The CI workflow runs `ruff check dashboard`, `pytest`, `git diff --check`, a raw
data tracking check, and a cache-only application-shell check. Local execution
is:

```powershell
pytest
ruff check dashboard
git diff --check
```

## Current unresolved evidence flags

- The clean store-visit scan records 223,342,163 raw rows with zero invalid rows
  and zero duplicate keys. Its dataset status remains partial only because two
  supplied markets combine four host cities and require explicit allocation.
- Boston has no supplied UHI points within the two-mile venue buffer and uses a
  partial market-level fallback.
- Dallas/Houston and Los Angeles/San Francisco store-visit markets are combined;
  equal city allocations remain partial and are never called city observations.
- GTFS is supplemental and currently unavailable in strict transit-weighted
  scoring until a pinned, hashed snapshot is refreshed.
- The current rolling demand audit reports 22 city/year holdouts. The candidate
  baseline beats the 364-day seasonal-naive comparator for all 11 cities in
  2024 and for none in 2023. It therefore remains labeled a scenario model,
  not a validated prediction.
- Under the supplied-data lens, 8 of 11 cities pass the strict evidence gate.
  Boston is held out by the two-mile UHI gap; Miami and New York/New Jersey are
  held out by weather-station distances above 30 miles.
