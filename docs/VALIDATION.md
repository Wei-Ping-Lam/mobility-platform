# Validation and release gates

## Data validation

- Expected partition counts are checked for every supplied dataset.
- Required columns, date ranges, numeric ranges, coordinates, nulls, and known sentinel values are checked.
- Combined market mappings are explicit and tested.
- GTFS feeds are checked for required files, valid coordinates, route counts, service times, and feed hashes.
- Artifact manifests record input and output row counts, coverage, warnings, and hashes.

## Model validation

- Readiness values remain in the 0–100 range.
- Weight profiles normalize to one.
- Transit improvements cannot reduce readiness.
- Higher heat or UHI cannot improve the corresponding safety score.
- Zero-intervention scenarios reproduce baseline capacity and emissions.
- A valid GTFS score of zero or five remains observed.
- Unavailable data never becomes a silent estimate.
- Demand metrics report MAE and WAPE against a seasonal-naive baseline.

## UI validation

- Cache-only startup works.
- Full-data startup works after ETL.
- Missing data produces an actionable warning.
- Evidence status is visible on headline metrics.
- Important charts have table equivalents.
- Scenario downloads reproduce displayed values.
- Executive, Explorer, and Methods views render at desktop and narrow widths.
