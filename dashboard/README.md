# FIFA 2026 Host City Transportation Decision Platform

Streamlit planning tool for the 11 US host cities. The competition-ready design
compares match-specific access gaps and transportation packages while exposing
source quality, assumptions, uncertainty, cost, and implementation constraints.

## Implementation status

Contract `0.3.0` is frozen. The current branch implements the Rice evidence
pipeline, evidence-gated MRS, generic planning scenarios, and Methods & QA
downloads. The following are **release targets pending workstream integration**:

- pinned official FIFA match schedule;
- event-valid agency GTFS snapshots;
- pinned five-mile OSM walking networks;
- cited EPA/FTA/FHWA factor registries;
- match-specific hourly movement and physical access gaps;
- city-specific intervention accounting and Pareto recommendations; and
- priority-corridor and three-package comparison views.

Do not demonstrate those targets as completed until `docs/VALIDATION.md` has a
passing release evidence record.

## Run locally

The dashboard reads compact artifacts and makes no startup network request.

```powershell
$env:MOBILITY_DATA_ROOT = "C:\path\to\Rice WC Hack"
python -m dashboard.pipeline.etl.build --data-root $env:MOBILITY_DATA_ROOT
python -m streamlit run dashboard/app.py
```

Public-source refresh commands are owned by their pipelines and must run
offline before dashboard launch. A URL or legacy GTFS score is not eligible
evidence without the required version, coverage, license, timestamp, and hash.

## Current product behavior

- **Executive:** venue map and evidence-gated Rice comparison. The default Rice
  lens excludes transit and is not a complete transportation ranking.
- **Explorer:** commercial-activity baseline, generic event planning band,
  climate/transit statuses, and current pressure/cost proxies.
- **Methods & QA:** coverage, formulas, assumptions, holdout validation,
  manifests, statuses, and downloads.

The current demand band is a planning scenario. Commercial visits are not match
attendance. GTFS is scheduled-service evidence, not ridership or reliability.
Current pressure outputs do not measure roadway congestion.

## Competition-ready behavior

After all release gates pass:

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
pytest dashboard/tests/integration
ruff check dashboard/tests/integration
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
