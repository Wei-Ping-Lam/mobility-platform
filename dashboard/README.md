# FIFA 2026 Host City Transportation Decision Platform

Streamlit planning tool for the 11 US host cities. The competition-ready design
compares match-specific access gaps and transportation packages while exposing
source quality, assumptions, uncertainty, cost, and implementation constraints.

## Implementation status

Contract `0.3.0` is frozen. The current branch implements Rice enrichment,
the 78-match official schedule snapshot, match-specific movement scenarios,
physical access contracts, six intervention types, Pareto recommendations,
three decision workspaces, and Methods & QA downloads. Cited factor ranges are
integrated as scenario/estimated evidence.

Transportation evidence remains incomplete after the explicit GTFS refresh:
38 matches have event-valid service evidence; four cities are observed, five are
partial, and Kansas City/Philadelphia remain unavailable. Pinned five-mile OSM
walking graphs now provide isochrones for all 11 venues and event-relevant stop
routes where GTFS eligibility permits. The UI suppresses capacity-qualified gaps
and marks recommendations partial wherever required evidence remains unavailable.

## Run locally

The dashboard reads compact artifacts and makes no startup network request.

```powershell
$env:MOBILITY_DATA_ROOT = "C:\path\to\Rice WC Hack"
uv sync --all-groups --locked
uv run python -m dashboard.pipeline.etl.build --data-root $env:MOBILITY_DATA_ROOT
uv run python -m streamlit run dashboard/app.py
```

Public-source refresh commands are owned by their pipelines and must run
offline before dashboard launch. A URL or legacy GTFS score is not eligible
evidence without the required version, coverage, license, timestamp, and hash.

## Current product behavior

- **Executive:** match demand, capacity-qualified gaps where eligible, partial
  investment screening, cost ranges, lead times, and evidence status. MRS is secondary.
- **Explorer:** official match selection, hourly movement, available Rice/OSM
  layers, three packages, before/after timelines, tradeoffs, and exact downloads.
- **Methods & QA:** source hashes, factors, network status, formulas, assumptions,
  holdout validation, rank sensitivity, manifests, and downloads.

The current demand band is a planning scenario. Commercial visits are not match
attendance. GTFS is scheduled-service evidence, not ridership or reliability.
Current pressure outputs do not measure roadway congestion.

## Competition-ready behavior

The implemented product behavior is:

- **Executive** leads with match, priority corridor, peak passenger gap,
  candidate investment, modeled outcome range, planning cost, lead time, and
  evidence quality. MRS is secondary.
- **Explorer** shows hourly movement, GTFS routes/stops, OSM isochrones, Rice
  heat/POI layers, and Baseline/Operational/Capital package comparisons.
- **Methods & QA** traces every headline number to a contract field, formula,
  source record, factor, validation result, and exact download.

## Canonical supplied data

All six supplied datasets are under local, read-only `Rice WC Hack/`:

| Dataset | Platform use |
| --- | --- |
| `store-visits-rice` | Commercial-activity context and baseline validation |
| `daily-weather-rice` | Heat context |
| `urban-heat-index-rice` | Venue and route-area UHI context |
| `spend-patterns-rice` | General customer-origin context |
| `core-poi-geometry-rice` | Venue-area destinations and amenities |
| `daily-spend-brand-and-state-rice` | Commercial-activity scenario context |

Combined markets and missing partitions remain visibly partial. Raw data are
never committed. FIFA, GTFS, OSM, EPA, FTA, and FHWA/PBIC sources are explicitly
supplemental; see [SOURCE_REGISTER.md](../docs/SOURCE_REGISTER.md).

## Verification and presentation

```powershell
uv run python -m pytest dashboard/tests/integration
uv run ruff check dashboard/tests/integration
git diff --check
```

- [Methodology](../docs/METHODOLOGY.md)
- [Model card](../docs/MODEL_CARD.md)
- [Validation gates](../docs/VALIDATION.md)
- [Evidence-to-claim matrix](../docs/EVIDENCE_TO_CLAIM_MATRIX.md)
- [Judging criteria](../docs/JUDGING_CRITERIA.md)
- [Demo script](../docs/DEMO_SCRIPT.md)

Presentation guardrails: do not describe a scenario as observed, a commercial
origin as a fan origin, an OSM path as an accessibility audit, scheduled service
as actual operations. A pressure proxy does not measure roadway congestion.
