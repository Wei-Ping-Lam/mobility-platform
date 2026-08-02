# FIFA 2026 Host City Transportation Decision Platform

## Submission metadata — blocking before submission

- **Team:** `[TEAM NAME REQUIRED]`
- **Primary contact:** `[NAME AND EMAIL REQUIRED]`
- **Submission date:** `[DATE REQUIRED]`

These placeholders are an explicit release blocker. They must be supplied by
the team; contributors must not invent names or contact details.

## Track 1 decision problem

Host cities need to identify where match-day access demand may exceed modeled
transport capacity and compare packages that could address the gap. The result
must show physical quantities, cost, lead time, evidence quality, and tradeoffs
without confusing commercial activity with match attendance or scheduled
service with actual operations.

## Proposed competition-ready solution

The platform is an evidence-backed Streamlit decision tool for all 11 US host
cities. It keeps the six `Rice WC Hack/` datasets as canonical supplied context
and uses separately pinned FIFA, GTFS, OpenStreetMap, EPA, FTA, and FHWA/PBIC
sources for match, network, service, emissions, and planning-cost evidence.

For a selected match, the current design:

1. create transparent low/base/high hourly arrival and departure scenarios;
2. compare peak passengers with scheduled transit-capacity ranges;
3. report network walking distance, service span, heat exposure, and residual
   passenger gap;
4. compare Baseline, Operational Package, and Capital Package outcomes; and
5. show Pareto tradeoffs across gap resolved, cost per passenger, net CO2e,
   lead time, and evidence quality.

MRS remains available as a secondary, sensitivity-tested policy index. Physical
gaps and intervention outcomes—not rank—lead the decision.

## Current implementation versus release acceptance

### Verified now

- Contract `0.3.0` defines versioned source, match, movement, access-gap,
  intervention, and recommendation records.
- The offline Rice ETL produces compact artifacts with QA, coverage, status,
  provenance, and hashes; the app does not scan raw data at startup.
- Combined source markets, missing weather coverage, and unavailable transit
  evidence remain visible rather than becoming silent estimates.
- The current demand implementation is compared with seasonal-naive. It won all
  11 city holdouts in 2024 and none in 2023, so it remains a planning scenario.
- Methods & QA exposes current formulas, assumptions, validation, and downloads.
- The official schedule snapshot maps 78 US-hosted matches to all 11 cities with
  local kickoff times and source hashes.
- Hourly movement, physical access, intervention accounting, city differentiation,
  Pareto screening, and all three UI workspaces are implemented and tested.
- EPA/FTA/FHWA inputs are pinned as scenario/estimated planning ranges.
- The GTFS refresh produced event-valid evidence for 50 matches across eight cities.
  Pinned, hash-checked event archives repaired Kansas City and Philadelphia;
  three cities remain wholly outside the event window.
- Five-mile OSM walking graphs and hashes cover all 11 venues; all venues retain
  isochrones, while event-relevant stop routes remain partial where GTFS is ineligible.

### Required before the competition-ready claim

- Repair the remaining outside-window feeds and match gaps so every city can
  support a capacity-qualified match access result.
- Run the final full-data, narrow-screen, and screenshot release record against the integrated branch.
- Replace the team/contact placeholders above.

Until those gates pass, movement and intervention values are planning scenarios,
capacity-qualified access gaps are withheld, and investment recommendations remain
partial screening options—not operational findings.

## Data and analytical reasoning

Rice commercial visits and spending provide temporal and economic context;
they are not match attendance or ticket-holder behavior. FIFA provides match
context. Event-valid GTFS supplies scheduled departures and service span. OSM
supports reproducible network distances and route coverage while leaving absent
sidewalk/accessibility tags unknown. Rice weather/UHI supports heat context.
EPA/FTA/FHWA references supply versioned planning ranges.

The model reports scheduled capacity as a range because vehicle capacity and
utilization are assumptions. It reconciles hourly flows to attendance scenarios
and preserves uncertainty. The intervention ledger includes added service VMT
and emissions, upstream park-and-ride travel, distance-limited bike uptake, and
pedestrian/cooling effects only when a documented outcome changes. Arrival
spreading shifts the peak without receiving an automatic emissions credit.

## Impact, feasibility, and legacy

The decision value is specificity: a city can see the gap, candidate actor,
dependencies, order-of-magnitude cost, lead time, and modeled outcome range.
Residents can inspect the same assumptions and evidence status. Operational and
capital packages make near-term and longer-term choices comparable without
claiming one universal optimum.

The contracts and offline source-refresh process are event-agnostic. Cities can
reuse them for concerts, ordinary high-demand days, heat planning, service
reviews, and post-event monitoring. Scenario estimates can later be compared
with observed counts, but the platform does not perform causal attribution.

## Visualization and communication

The release Executive view answers where, why, what investment, what modeled
outcome, at what cost/lead time, and with what confidence. Explorer combines
hourly bands with routes, stops, network isochrones, UHI, POIs, and scenario
tradeoffs. Methods & QA maps every headline metric to its contract field,
source, hash, factor, assumptions, and test status. Major charts require table
equivalents and exact downloads.

Use [DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) and
[EVIDENCE_TO_CLAIM_MATRIX.md](docs/EVIDENCE_TO_CLAIM_MATRIX.md) for the final
presentation. Current run-specific values must come from the integrated app and
release evidence record, not this narrative.

## Responsible limits

- The educational Rice datasets contain noise and spatial jitter.
- The platform does not observe match attendance, fan origins, actual mode
  choice, service reliability, queues, crashes, or roadway performance.
- GTFS describes schedules; OSM tags do not certify route condition,
  accessibility, or safety.
- Emissions and costs are planning ranges, not a local fleet inventory,
  engineering estimate, bid, or funding commitment.
- Scenario differences are not observed outcomes or causal effects.
