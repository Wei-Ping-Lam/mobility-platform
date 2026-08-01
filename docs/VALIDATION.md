# Validation and release gates

## Data validation

- All six dataset directories are required for a full ETL run.
- The expected 4 x 8 partition grid is enumerated. The supplied missing
  `daily-weather-rice_2_0_0.csv.gz` partition is surfaced as partial coverage.
- Required columns, duplicate keys, dates, numeric ranges, coordinates, nulls,
  canonical market labels, and known weather sentinels are recorded per input
  chunk without retaining raw rows.
- Raw-to-derived row counts, coverage warnings, generation times, and SHA-256
  artifact hashes are written to `manifest.json` and `qa_report.json`.
- Combined source markets are tested against exact mappings; substring matching
  is prohibited.
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
