# FIFA 2026 Host City Mobility Readiness Platform

## Track 1: Transportation & Access

**Team:** [add team metadata]
**Contact:** [add contact metadata]
**Submission date:** 2026

### The decision problem

FIFA 2026 host cities need a way to compare venue access and identify where
first/last-mile investments, heat protections, and event transport capacity are
most urgent. A useful tool must expose evidence quality as clearly as it shows
the result: retail visits are not stadium attendance, a GTFS feed is not
ridership, and a scenario is not a forecast.

### The solution

The platform is an evidence-first Streamlit decision-support tool for the 11
US host cities. It combines six supplied datasets with a separately pinned
GTFS snapshot and produces compact, reproducible artifacts through an offline
ETL. Decision-makers can compare cities, inspect venue-centered evidence, test
transport interventions, and download the exact metrics and assumptions shown
on screen.

The application has three modes:

1. **Executive**: an evidence-gated city comparison, venue map, MRS table,
   first/last-mile gap indicators, and priority evidence gaps.
2. **Explorer**: historical commercial-activity demand proxies, low/base/high
   event scenarios, transit and climate evidence, editable capacity controls,
   pressure/emissions proxies, and a commercial-activity scenario range.
3. **Methods & QA**: dataset coverage, source and artifact manifests, formula
   definitions, validation metrics, assumptions, statuses, and downloads.

### Evidence and analytics

The headline Mobility Readiness Score (MRS) is a weighted average of four
venue-centered components:

- transit access from the pinned GTFS snapshot;
- heat safety from host-station weather and a NOAA heat-index calculation;
- UHI safety from urban-heat points near the venue; and
- venue-support density from POIs within one mile.

The default Balanced profile is 35% transit, 20% heat, 15% UHI, and 30% venue
support. Additional named profiles and custom weights are available. Weights
are normalized and every component is clipped to the 0-100 scale.

An incomplete city keeps a weighted-available partial MRS for auditability, but
its explicit `rankable` flag is false until every non-zero-weight core
component is evidence-eligible. Estimated values require an explicit opt-in.
No missing feed or metric silently becomes an expert score.

The demand baseline uses 2022-2024 data with a 2022-2023 seasonal/weekday
profile and a 2024 holdout report. The event range is a scenario band, not a
confidence interval. Traffic results are labeled pressure proxies: capacity,
potential mode shift, residual vehicle trips, vehicle-kilometers, and an
emissions range. They do not claim to measure roadway congestion, queues, or
actual fan mode choice.

Economic activity is also a scenario. It uses observed 2022-2024 commercial
spend as a baseline and explicit low/base/high uplift assumptions. It is not
causal attribution, stadium attendance, or a forecast of local GDP.

### Why this creates impact

The tool converts a broad sustainability question into actionable comparisons:

- agencies can see where venue transit evidence is weak or unavailable;
- host-city teams can identify heat-exposed access gaps and test capacity;
- residents can inspect the assumptions behind intervention benefits; and
- planners can preserve the ETL, manifests, validation reports, and contracts
  for post-tournament mobility and resilience work.

The same workflow supports future event planning and ordinary high-demand
days. Its explicit provenance, partial-market allocation, pinned feed hashes,
and downloadable scenarios make follow-up measurement possible after 2026.

### Data provenance

The offline ETL processes:

| Dataset | Derived output | Use |
| --- | --- | --- |
| `store-visits-rice` | daily and category-level visits | demand proxy and validation |
| `daily-weather-rice` | city-day weather | heat exposure |
| `urban-heat-index-rice` | city and venue-buffer UHI | heat resilience |
| `spend-patterns-rice` | visitor-origin and spend summaries | origin context |
| `core-poi-geometry-rice` | venue-area POI counts | venue-support proxy |
| `daily-spend-brand-and-state-rice` | city/state daily activity | economic scenario baseline |

The ETL records partition counts, row counts, hashes, dates, duplicate keys,
invalid values, coordinate checks, nulls, and known weather sentinels. The
documented missing weather partition is surfaced as partial coverage. Combined
Dallas/Houston and Los Angeles/San Francisco source markets use explicit equal
allocation and remain visibly partial rather than being assigned by substring.

GTFS snapshots record URL, fetch time, content hash, agency, required files,
calendar validity, service span, event-window departures, stop counts, route
counts, venue coordinates, nearest-stop distance, and feed status. A valid
zero-service score remains observed zero; a failed feed remains unavailable.

### Demonstration script

1. Open **Executive** and explain why gray/incomplete cities remain visible but
   are not ranked.
2. Select a city in **Explorer** and distinguish observed evidence from the
   modeled event range.
3. Set shuttle, park-and-ride, bike, and pedestrian controls to zero, then
   increase them and show the nonnegative capacity, residual-pressure, and
   emissions changes.
4. Open **Methods & QA** and download the city metrics and manifest. Show that
   the displayed data, statuses, formulas, and assumptions are reproducible.

### Limits and responsible interpretation

- The supplied data are noisy, transformed educational data; results are
  methodology demonstrations rather than certified city assessments.
- Retail visits and commercial spend are not ticketed-fan observations.
- GTFS describes scheduled service and stop proximity, not ridership,
  reliability, accessibility, or congestion.
- POI density does not establish a safe, shaded, or ADA-compliant route.
- Equal allocation of combined markets is a transparent partial-evidence
  assumption, not a city-specific measurement.
- The platform does not include roadway network, signal, parking occupancy,
  crash, emissions-monitor, or pedestrian-count data.

The authoritative implementation references are
[`dashboard/README.md`](dashboard/README.md),
[`docs/MODEL_CARD.md`](docs/MODEL_CARD.md), and
[`docs/VALIDATION.md`](docs/VALIDATION.md). The Methods & QA view is the
source of current run-specific numbers; this narrative intentionally avoids
hard-coded rankings and unsupported outcome claims.
