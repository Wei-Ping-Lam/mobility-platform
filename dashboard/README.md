# FIFA 2026 Host City Transportation Decision Platform

Streamlit planning tool for the 11 US host cities. The competition-ready design
compares match-specific access gaps and defined single-measure investments while exposing
source quality, assumptions, uncertainty, cost, and implementation constraints.

## Implementation status

Contract `0.3.0` is frozen. The current branch implements Rice enrichment,
the 78-match official schedule snapshot, match-specific movement scenarios,
reconciled broad visitor-origin and venue-approach mode scenarios,
physical access contracts, six intervention types, match-scoped nondominated option sets,
four decision workspaces, and exact Methods downloads. Cited factor ranges are
integrated as scenario/estimated evidence.

An independently versioned operational snapshot adds 33 official post-event
benchmarks across all 11 cities plus 13 match-level wide records for Houston,
New York/New Jersey, and San Francisco. Raw
official pages remain ignored locally; the tracked artifact retains their
content hashes, publication metadata, metric locations, and semantic limits.
These aggregates do not silently recalibrate match-hour scenarios.

Recommendation policy is explicit: qualified screening options are separated
from exploratory sensitivities, total cost remains visible, and reusable capital
uses an auditable event-use comparison basis. Arrival management is exploratory
until observed response, curb throughput, and shoulder capacity are supplied.

The explicit GTFS refresh now supplies hash-checked event-window calendar
evidence for all 78 matches across all 11 cities. It also finds 29 matches with
zero scheduled capacity in the half-mile venue catchment; this is a visible
planning red flag, not a missing-value fallback. Five-mile OSM walking graphs
provide isochrones for every venue and event-relevant stop routes for eight.
All 78 transit gaps are capacity-qualified; 23 match results in Boston, Dallas,
and Miami remain partial for stop-route and route-heat evidence.

NOAA Global Hourly supplements replace only the distant Rice weather stations
for Miami and New York/New Jersey. A five-scene USGS Landsat surface-temperature
analysis replaces only Boston's missing venue-buffer UHI row. These additions
make all 11 cities strictly MRS-rankable while retaining their non-Rice source
labels and semantic limits.

## Run locally

Prerequisites are Git and uv `0.11.16` or newer. A fresh clone runs from the
tracked compact artifacts; the 6.8 GB Rice source collection is not required
for dashboard preview and no startup network request is made.

```powershell
uv python install 3.11
uv sync --all-groups --locked
uv run python -m streamlit run dashboard/app.py
```

To rebuild the Rice-derived artifacts, point the offline ETL at the separately
provided local source collection:

```powershell
$env:MOBILITY_DATA_ROOT = "C:\path\to\Rice WC Hack"
uv run python -m dashboard.pipeline.etl.build --data-root $env:MOBILITY_DATA_ROOT
```

Public-source refresh commands are owned by their pipelines and must run
offline before dashboard launch. A URL or legacy GTFS score is not eligible
evidence without the required version, coverage, license, timestamp, and hash.

To refresh the official operational reports explicitly:

```powershell
uv run python -m dashboard.pipeline.public.operations --refresh --retrieved-at 2026-08-02T18:00:00Z
uv run python -m dashboard.pipeline.public.environment --refresh --retrieved-at 2026-08-02T18:00:00Z
uv run python -m dashboard.pipeline.public.validate
```

Review every manually transcribed operational metric against its `source_locator` before
committing a refreshed artifact. The refresh never runs during Streamlit use.

If Windows blocks a uv-generated console-script shim with `os error 5`, use the
project interpreter directly: `.venv\Scripts\python.exe -m streamlit run dashboard/app.py`.

## Current product behavior

- **Portfolio Overview:** five objective tabs keep all 11 cities visible: Resilience,
  Visitor movement, First/last mile, Investments & strategies, and Outcomes. The
  default starts with readiness and a common physical stress test. Visitor movement
  compares city-tournament origin mix, approach-mode mix, and peak timing without
  implying exact visitor locations or routes; exact tables and a
  direct link to the largest-gap action plan support drill-down without a map or city filter.
- **City Action Plan:** a concise problem/why/action story with a defined measure scale,
  comparison cost, peak benefit, owner, lead time, dependencies, and evidence gate.
- **Scenario Explorer:** official match selection, hourly movement, a modeled venue-area
  traffic-pressure comparison, selectable Rice/GTFS/OSM layers, defined single measures,
  advanced composite sensitivity tests, before/after timelines, and exact downloads.
- **Methods:** source hashes, factors, network status, formulas, assumptions,
  holdout validation, rank sensitivity, manifests, and downloads.

The current demand band is a planning scenario. Commercial visits are not match
attendance. GTFS is scheduled-service evidence, not ridership or reliability.
Current pressure outputs do not measure roadway congestion.

## Competition-ready behavior

The implemented product behavior is:

- **Portfolio Overview** keeps all 11 cities visible at once and maps each tab directly
  to a Track 1 objective. Movement forecasts broad origin and approach-mode scenarios
  across every hosted match and separates arrival and departure scenario peaks;
  first/last mile combines exact-hour scheduled capacity with event-stop walking evidence;
  recommendations show bottleneck-matched concrete measures; and Access, Traffic, and
  CO2e outcomes remain separately selectable with explicit units and limitations.
- **City Action Plan** leads with the access challenge, readiness components,
  candidate investment, modeled outcome range, planning cost, lead time, and
  evidence quality. MRS is secondary.
- **Scenario Explorer** shows hourly movement, GTFS routes/stops, OSM isochrones, Rice
  heat/POI layers, and Baseline/Operational/Capital vehicle-trip pressure comparisons.
- **Methods** traces every headline number to a contract field, formula,
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
