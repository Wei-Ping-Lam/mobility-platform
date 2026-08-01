# FIFA 2026 Host City Mobility Readiness Platform

Evidence-first Streamlit dashboard for comparing venue access, heat exposure,
transit evidence, demand pressure, and transparent intervention scenarios across
the 11 U.S. FIFA 2026 host cities.

## Run the dashboard

The dashboard reads compact derived artifacts. It does not scan raw datasets at
startup.

```powershell
$env:MOBILITY_DATA_ROOT = "C:\path\to\Rice WC Hack"
python -m dashboard.pipeline.etl.build --data-root $env:MOBILITY_DATA_ROOT
python dashboard/fetch_gtfs.py --output data
python -m streamlit run dashboard/app.py
```

If the ETL has not been run, the app can display legacy checked-in cache data,
but it will show compatibility warnings and strict rankings will be limited.

## Views

### Executive

- Evidence-gated readiness map and ranking.
- Actual stadium coordinates.
- Priority city cards and gap summaries.
- Observed, derived, partial, estimated, unavailable, and scenario badges.

### Explorer

- City-level demand baseline and World Cup scenario range.
- Venue-level transit and climate comparison.
- Shuttle, bike-share, park-and-ride, and pedestrian scenario controls.
- Potential mode shift, residual vehicle pressure, emissions proxy, and cost.
- Downloadable scenario JSON.

### Methods & QA

- Artifact manifest and freshness.
- Dataset coverage by city.
- Formula and assumption register.
- Demand holdout validation.
- City-metrics and manifest downloads.

## Offline ETL outputs

The ETL consumes all six supplied datasets:

| Artifact | Source |
| --- | --- |
| `visits_daily.parquet` | `store-visits-rice` |
| `visits_daily_category.parquet` | `store-visits-rice` |
| `weather_city_daily.parquet` | `daily-weather-rice` |
| `uhi_city_summary.parquet` | `urban-heat-index-rice` |
| `spend_origins.parquet` | `spend-patterns-rice` |
| `poi_venue_summary.parquet` | `core-poi-geometry-rice` |
| `brand_spend_city_daily.parquet` | `daily-spend-brand-and-state-rice` |
| `manifest.json` and `qa_report.json` | ETL provenance and QA |

Combined source markets are allocated equally across their constituent cities
and are marked as partial evidence. No substring-based city matching is used.

## GTFS policy

GTFS results are pinned snapshots. The snapshot records feed URLs, timestamps,
SHA-256 hashes, required-file status, route counts, stops, scheduled departures,
service hours, and venue distances.

A valid zero-service result is observed evidence. A failed or unavailable feed
has no score and is never silently replaced by an expert estimate.

## Analytical honesty

- Retail and commercial foot traffic is a mobility-demand proxy, not stadium attendance.
- Event demand bands are scenarios unless holdout validation supports predictive language.
- Traffic outputs estimate vehicle pressure and capacity displacement; they do not measure roadway congestion.
- Estimated values require explicit opt-in and are excluded from the default strict ranking.
- All source coverage, assumptions, and statuses are visible in the Methods & QA view.

## Tests and parallel work

Run tests from the repository root:

```powershell
pytest
ruff check dashboard
git diff --check
```

See [WORKSTREAMS.md](../WORKSTREAMS.md) for branch, worktree, ownership, and
integration rules.
