# Validation and release acceptance

This file distinguishes checks supported by the current branch from gates that
must pass after all workstreams integrate. A contract field or fixture is not a
completed analytical result.

## Current verified foundation

- Contract version is `0.3.0`; its source, match, movement, access-gap,
  intervention, and recommendation records are serializable.
- The application shell reads compact artifacts rather than raw Rice files.
- All six Rice datasets retain exact source names, QA reports, and artifact
  hashes; raw data remain local and untracked.
- Missing weather coverage, combined markets, alternate origin schemas, and
  evidence statuses are surfaced.
- Current score bounds, weight normalization, heat/UHI monotonicity, and
  negative-input rejection have automated checks.
- Current demand validation reports 22 holdouts: the candidate beats the
  seasonal-naive comparator in 2024 for 11 cities and in 2023 for zero. It is
  therefore a planning scenario, not a validated prediction.
- The 2026-08-02 GTFS refresh produced event-valid, hash-checked calendar
  evidence for all 78 matches and observed feed status for all 11 cities. A
  valid feed is not proof of service at the venue: 29 matches have observed zero
  scheduled capacity within the half-mile catchment. No legacy score became
  observed without source, hash, and event-window evidence.

## Release data gates

- All 11 cities map to official matches, venues, GTFS agencies, and five-mile
  OSM extracts.
- Every supplemental artifact records URL, publisher, retrieval time, version,
  license, coverage, status, and SHA-256.
- FIFA local kickoff times and venue mappings are checked against the pinned
  source; duplicate match IDs and invalid time zones fail release.
- GTFS checks required files, event-date calendars/exceptions, stop times,
  frequencies, shapes, transfers/pathways when present, and agency coverage.
- OSM checks extract bounds/date, connected venue component, distance units,
  edge geometry, detour ratios, tag coverage, and ODbL attribution.
- Factor registries record exact source release/year, units, conversions,
  inflation basis where relevant, low/base/high values, and hashes.
- Cache-only startup performs no network or raw-data calls.
- Missing feeds, incomplete networks, and absent accessibility tags remain
  visible and cannot become estimates silently.
- The operational snapshot covers all 11 cities, contains 33 source-located
  metrics and 13 match-level records, and keeps every city explicitly
  `match_hour_calibration_ready: false` until interval-level evidence exists.
- Every operational metric has a physical unit, granularity, source locator,
  permitted calibration use, and prohibited-use list. Tampering fails the
  artifact-hash gate.
- The environmental supplement contains 366 daily NOAA rows for Miami and New
  York/New Jersey, each with at least 18 hourly observations and a station under
  five miles from its venue. Boston contains five valid Landsat scenes and
  169,940 venue-buffer pixels. Snapshot tampering fails closed.

## Release model gates

- Hourly arrivals and departures reconcile to each attendance scenario; zero
  matches create zero event demand.
- Every match-level visitor-flow origin allocation and mode allocation reconciles
  exactly to low/base/high attendance; city-tournament totals equal the sum of
  that city's hosted matches.
- A later-stage international scenario is never lower than the corresponding
  group-stage scenario. Higher transit readiness or scheduled coverage cannot,
  all else equal, reduce the scheduled-transit scenario share.
- Higher attendance cannot reduce peak demand or the access gap.
- More eligible scheduled capacity cannot increase the transit gap.
- Longer network distance or higher heat cannot improve access.
- Network distance is not shorter than straight-line distance beyond documented
  numerical tolerance.
- Transit capacity is reported as a range and never presented as ridership.
- Zero intervention reproduces baseline exactly.
- Every displayed control changes its documented outcome.
- Shuttle/additional-service VMT and emissions are included; park-and-ride
  preserves upstream VMT, requires feeder capacity, and includes feeder VMT and
  operations cost; arrival spreading creates no direct emissions credit.
- A GTFS vehicle serving multiple nearby stops is counted once by static
  `trip_id` or expanded frequency occurrence, then matched to the exact peak
  hour and event phase used by the demand model.
- Costs, capacities, trips, and absolute VMT inputs remain physically valid;
  net VMT and net CO2e may be negative when a package performs poorly.
- Identical packages produce different outcomes for fixture cities with
  different schedules, networks, service, heat, or demand.
- Observed, calibrated, validated, or predictive-accuracy language is blocked
  unless both holdout years beat seasonal-naive and fan-specific origin/mode
  calibration evidence is supplied. The permitted label is “scenario forecast.”
- All named MRS profiles publish weight sensitivity and rank stability; missing
  transit makes transportation-weighted profiles unrankable.

## Release UI and presentation gates

- Portfolio starts with all 11 cities and has no city filter or map. It leads with the
  readiness ranking and its four criterion scores, then separates visitor movement,
  first/last mile, investment screens, and Access/Traffic/CO2e outcomes into their own
  tabs with exact tables and explicit claim boundaries. Visitor movement uses one
  compact segmented view for origin mix, mode mix, and peak timing.
- City Action Plan answers the access challenge, readiness drivers, candidate investment, modeled outcome, cost,
  lead time, evidence quality, and evidence-gated time horizons.
- Portfolio separates physical access priority, strict readiness, and qualified single-measure screens.
  Cost per passenger for the common added-frequency measure is not used as a cross-city
  portfolio lens because the shared scale and national unit factors make it identical.
- Scenario Explorer supports match selection and clearly labels Baseline, Operational Package, and
  Capital Package as composite sensitivity tests, alongside modeled venue-area vehicle-trip pressure, routes,
  stops, isochrones, UHI, POIs, and origin-context layers.
- Every major visualization has labels, provenance, status, uncertainty where
  relevant, plain-language interpretation, and a table equivalent.
- Scenario downloads reproduce displayed values exactly.
- Missing GTFS/OSM layers show actionable warnings without breaking Rice views.
- All 11 cities pass desktop, narrow-layout, and AppTest checks.
- Presentation metric names map to contract fields, and static checks reject
  prohibited positive claims about congestion, visitor prediction, ADA
  compliance, causal effects, and observed mode shift.
- Team/contact placeholders are replaced by the team before submission.

## Release evidence record — 2026-08-02

- Environment: uv 0.11.16, CPython 3.11, committed lockfile, and project `.venv`;
  no machine-specific preview runtime is referenced.
- Automated suite: `194 passed` in bounded ETL, public, model/GTFS,
  integration, nonvisual UI, workspace, and all-city AppTest partitions; Ruff,
  `uv lock --check`, public snapshot validation, and `git diff --check` pass.
- Public cache validator: 78 schedule events, 26 planning factors, 11 GTFS city
  records, and 11 graph-derived walking records; validator passed.
- GTFS content artifact SHA-256:
  `c407473a29db9e71a2278fa73f7cc8fa2dcf72316ef6e84270c4b91e4c3f78d1`.
  It contains 78 event-valid match records, 2,694 venue-area stops, and 520
  bounded route shapes across 15 pinned agency feeds and 11 observed cities.
  Boston (7 matches), Dallas (9), Miami (7), and six New York/New Jersey
  matches have observed zero scheduled capacity in the half-mile catchment.
- OSM content artifact SHA-256:
  `ec8aa95baa28a93b10d919dba408131d0cd27c36a256f8b10057b4f71a46992e`.
  All 11 venues have five-mile graph-derived isochrones; eight have a network
  path to an event-relevant GTFS stop. Boston, Dallas, and Miami remain partial
  for stop-route and route-heat evidence rather than receiving invented paths.
- Factor artifact SHA-256:
  `6115126eb452e44807a7718a7242b57593dbc1c6c4e20841d133a17b85f5d652`.
  Production composition fails on missing/incomplete factors and every outcome
  includes this hash in its assumptions.
- Operational evidence artifact SHA-256:
  `412595aa8402eadee12940a32167238b4182c5aaa0008fee14b9913f2ff866b0`.
- Operational source review terms were found in all 11 pinned responses; snapshot generation fails when a required review term is absent.
  It contains 11 content-hashed official source records, 33 post-event
  benchmarks across all cities, and 13 match-level records without filling
  unreported fields.
- Environment evidence artifact SHA-256:
  `9b60e5e6b3f2acda78b10ef08478af485383ba3283f92d8ddc9ad75bc18029de`.
  Its NOAA source hashes are `087e554002f51bff3fafe134bb9c494bdefcd5df031cf677b54251e1923d5772`
  and `01e1f9d724dfe4857d16595eec9803194153fc5ec747efc7745d7552399eb955`;
  its Landsat-derived source hash is `16470dd96ad77e4b271e0cbf17c80997a6eb70288d4d005254fac3681f0bb4bd`.
- Streamlit AppTest: Portfolio, City Action Plan, Scenario Explorer, and Methods
  render without an exception. All 78 movement timelines and before/after tables
  pass nonempty, reconciliation, and peak-reduction checks.
- Recommendation identity: all 260 nondominated records retain an exact
  `match_id`; 190 are evidence-qualified screening options and 70 are
  exploratory arrival-management sensitivities. The set contains 71
  added-frequency, 71 shuttle, 48 route/heat-qualified cooling, and 70 bounded
  arrival-management records. Seven Atlanta matches have no intervention record
  because modeled scheduled capacity leaves no residual peak gap to resolve.
- Arrival-management behavior: effective spreading uses eligible share ×
  compliance and a shoulder-capacity limit. Median match-level gap credit fell
  from about 4,504 to 1,317 passengers/hour; it receives no vehicle-trip or
  emissions credit and is never evidence-qualified without local response and
  curb data.
- Access evidence: all 78 gaps are capacity-qualified; 55 have scenario status
  with complete modeled route/heat components and 23 are partial for those
  components. Zero scheduled capacity remains a qualified observed result.
- All-city comparison: all 11 cities are strictly rankable under every named
  MRS profile. Boston's missing venue UHI is replaced by the pinned Landsat
  supplement; Miami and New York/New Jersey's distant Rice weather stations are
  replaced by pinned venue-proximate NOAA observations. MRS remains secondary
  and does not make match-hour scenarios validated predictions.
- Portfolio accounting: match, city-tournament, and U.S.-tournament tests verify
  one-time capital per city, recurring event operations, and default exclusion
  of partial/unavailable access results.
- Local project-owned Streamlit preview: cache-only health check returned HTTP
  200 at `http://127.0.0.1:8513` after the portfolio-first landing integration.
- Screenshot record: failed because the in-app browser sandbox-policy handshake
  blocked localhost control. No desktop/narrow screenshot claim is made.
- Known release limitations: published GTFS does not include confirmed FIFA
  special-event overlays; 29 match records show zero scheduled half-mile
  capacity and 23 lack a stop-route/route-heat path. Team/contact metadata and final desktop/narrow
  screenshot review remain outstanding.

This is a competition MVP validation record, not certification for operational
traffic management.

Run W6-owned checks from the repository root:

```powershell
uv run python -m pytest dashboard/tests/integration
uv run ruff check dashboard/tests/integration
git diff --check
```
