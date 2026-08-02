# FIFA 2026 Host City Transportation Decision Platform

Streamlit planning tool for the 11 US host cities. The competition-ready design
compares match-specific access gaps and transportation packages while exposing
source quality, assumptions, uncertainty, cost, and implementation constraints.

## Implementation status

Contract `0.3.0` is frozen. The current branch implements Rice enrichment,
the 78-match official schedule snapshot, match-specific movement scenarios,
physical access contracts, six intervention types, match-scoped Pareto recommendations,
four decision workspaces, and exact Methods & QA downloads. Cited factor ranges are
integrated as scenario/estimated evidence.

Transportation evidence remains incomplete after the explicit GTFS refresh:
50 matches across eight cities have event-valid service evidence; six cities are
observed and five are partial. Pinned event-period archives repaired Kansas City
and Philadelphia without promoting a legacy score. Five-mile OSM walking graphs
provide isochrones for all 11 venues and event-relevant stop routes for seven.
The UI suppresses capacity-qualified gaps wherever required evidence remains unavailable.
Twenty-nine match access results currently pass the complete capacity-and-network
qualification gate; 21 remain partial and 28 unavailable.

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

- **Decision Brief:** a guided where/why/what/outcome/confidence story, explicit
  judging-criteria evidence, required-deliverable ledger, and evidence-gated time horizons.
- **Compare Cities:** strict ranking for eligible evidence plus a separate all-city
  screening order with conservative evidence ranges and exact exclusion reasons.
- **City & Match:** official match selection, hourly movement, selectable Rice/GTFS/OSM
  layers, three packages, before/after timelines, tradeoffs, and exact downloads.
- **Methods & QA:** source hashes, factors, network status, formulas, assumptions,
  holdout validation, rank sensitivity, manifests, and downloads.

The current demand band is a planning scenario. Commercial visits are not match
attendance. GTFS is scheduled-service evidence, not ridership or reliability.
Current pressure outputs do not measure roadway congestion.

## Competition-ready behavior

The implemented product behavior is:

- **Decision Brief** leads with match, access evidence, peak passenger gap,
  candidate investment, modeled outcome range, planning cost, lead time, and
  evidence quality. MRS is secondary.
- **Compare Cities** keeps all 11 cities visible without presenting partial evidence
  as a strict rank.
- **City & Match** shows hourly movement, GTFS routes/stops, OSM isochrones, Rice
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
