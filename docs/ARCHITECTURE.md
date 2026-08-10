# Project architecture

The repository is organized so evidence, analytics, and presentation can change
independently. The allowed dependency direction is:

```text
pipeline / snapshots
        ↓
mobility_platform contracts
        ↓
models → domain composition
        ↓
viz → ui pages
        ↓
dashboard/app.py
```

Code should not import upward. In particular, models and domain modules must not
import Streamlit, UI pages must not read raw source files, and the app shell must
not contain analytical formulas.

## Package boundaries

| Area | Responsibility | Primary tests |
| --- | --- | --- |
| `dashboard/pipeline/` | Offline ingestion, normalization, source gates, and snapshot generation | `dashboard/tests/etl/`, `gtfs/`, `public/` |
| `dashboard/mobility_platform/` | Stable contracts, paths, source metadata, mappings, and quality types | contract and integration tests |
| `dashboard/models/` | Pure movement, access, resilience, visitor-flow, intervention, traffic-strategy, and strategy-calibration calculations | `dashboard/tests/models/`, `interventions/` |
| `dashboard/domain/` | Joins model outputs into city, match, and portfolio decision artifacts | model and integration tests |
| `dashboard/viz/` | Chart construction from prepared frames; no data loading | `dashboard/tests/ui/test_maps.py` |
| `dashboard/ui/` | Streamlit presentation, page state, and navigation policy | `dashboard/tests/ui/` |
| `dashboard/app.py` | Cache-only composition root and public application shell | AppTest and release gates |

### Portfolio objective ownership

The Portfolio is composed from independently owned modules under
`dashboard/ui/portfolio/`:

| Objective | Renderer |
| --- | --- |
| Resilience | `resilience.py` |
| Visitor movement | `visitor_movement.py` |
| First/last mile | `first_last_mile.py` |
| Investments & transit | `investments.py` |
| Traffic management | `traffic_management.py` |
| Outcomes | `outcomes.py` |

`context.py` is the only analytics-to-UI adapter, `tables.py` owns exact-value
display schemas, and `page.py` only creates tabs and the page-level drill-down.
Objective renderers must not import models/domain modules or one another. This
lets separate contributors edit different objectives without touching the same
file or duplicating analytical formulas.

City-only traffic presentation lives in `dashboard/ui/city/traffic_plan.py`.
It consumes the same serialized match plan as the Portfolio adapter, so the
map and chronological actions do not introduce UI formulas.
`dashboard/viz/strategy_overlap.py` separately owns the city overlap maps: one
for the venue service screen against GTFS/walking evidence and one for the
selected GTFS transfer anchor against the retained candidate shortlist. The
portfolio remains map-free.

## Public and deferred workspaces

`dashboard/ui/workspaces.py` is the single navigation policy seam. The public
product currently exposes only Portfolio and City action plan. Scenario Explorer
and Methods remain implemented but are registered as deferred and are not
imported by the public app shell. Restoring a deferred workspace requires an
integration-owned change to the registry, shell, CTA tests, and product docs.

## Two-person ownership model

The lowest-conflict split is:

| Owner | Normal scope | Avoid without coordination |
| --- | --- | --- |
| Analytics/evidence owner | `dashboard/pipeline/`, `dashboard/models/`, model/public/ETL tests | app shell, workspace registry, shared contracts |
| Product/decision owner | `dashboard/ui/`, `dashboard/viz/`, `dashboard/domain/overview.py`, UI tests, product copy | snapshot schemas, factors, shared contracts |

The following are integration seams and should have only one active editor at a
time: `dashboard/app.py`, `dashboard/ui/workspaces.py`,
`dashboard/mobility_platform/contracts.py`,
`dashboard/domain/decision_support.py`, `dashboard/ui/portfolio/context.py`,
`dashboard/ui/portfolio/page.py`, `dashboard/ui/portfolio/shared.py`,
`dashboard/ui/portfolio/tables.py`, `pyproject.toml`, and `uv.lock`.

When an analytics change needs UI exposure, the analytics owner first lands a
pure model plus tests. A short follow-up integration commit wires its output into
`decision_support.py`. The product owner then consumes the stable output without
editing the model. This sequence avoids a branch that simultaneously rewrites
the model, composition layer, and page.

## Feature-extension pattern

1. Add or change one pure module under `dashboard/models/`.
2. Add focused tests in the matching test directory.
3. Expose a serializable result through the domain composition seam.
4. Build any chart under `dashboard/viz/` from a prepared frame.
5. Render it from a page without duplicating formulas.
6. Update the equation/assumption/claim documentation when the metric is new.

See `WORKSTREAMS.md` for branches, worktrees, path ownership, and handoff rules.

## Strategy calibration boundary

`dashboard/models/strategy_calibration.py` classifies a broad operating family
from scheduled coverage, stop proximity, walking evidence, network scale, and
regional-hub structure. It never reads a city name or official benchmark.
`dashboard/domain/decision_support.py` performs the benchmark comparison only
after prediction. The reviewed labels live in the separately validated
`world_cup_2026_strategy_benchmarks.json` snapshot. Exact published hubs,
windows, and controls may remain in source-audit artifacts, but do not override
the common generated plan or appear in the normalized city comparison. This
separation prevents the official answer from becoming a hidden runtime rule.
