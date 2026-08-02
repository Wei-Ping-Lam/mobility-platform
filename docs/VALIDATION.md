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

## Release model gates

- Hourly arrivals and departures reconcile to each attendance scenario; zero
  matches create zero event demand.
- Higher attendance cannot reduce peak demand or the access gap.
- More eligible scheduled capacity cannot increase the transit gap.
- Longer network distance or higher heat cannot improve access.
- Network distance is not shorter than straight-line distance beyond documented
  numerical tolerance.
- Transit capacity is reported as a range and never presented as ridership.
- Zero intervention reproduces baseline exactly.
- Every displayed control changes its documented outcome.
- Shuttle/additional-service VMT and emissions are included; park-and-ride
  preserves upstream VMT; arrival spreading creates no direct emissions credit.
- Costs, capacities, trips, and absolute VMT inputs remain physically valid;
  net VMT and net CO2e may be negative when a package performs poorly.
- Identical packages produce different outcomes for fixture cities with
  different schedules, networks, service, heat, or demand.
- Forecast language is blocked unless both holdout years beat seasonal-naive.
- All named MRS profiles publish weight sensitivity and rank stability; missing
  transit makes transportation-weighted profiles unrankable.

## Release UI and presentation gates

- Decision Brief answers where, why, candidate investment, modeled outcome,
  cost, lead time, and evidence quality without relying on MRS. It also exposes
  criterion evidence, required deliverables, and evidence-gated time horizons.
- Compare Cities separates strict eligible ranks from an all-city evidence screening.
- City & Match supports match selection and Baseline, Operational Package, and
  Capital Package comparison with routes, stops, isochrones, UHI, POIs, and
  origin-context layers.
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
- Automated suite: `178 passed`; Ruff, `uv lock --check`, public snapshot
  validation, and `git diff --check` pass.
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
- Streamlit AppTest: Decision Brief, Compare Cities, City & Match, and Methods & QA
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
- All-city comparison: eight cities are strictly rankable under the default
  balanced MRS profile. All 11 receive a separate physical access-priority
  order; Boston is excluded from strict MRS by venue UHI coverage, while Miami
  and New York/New Jersey are excluded by distant supplied weather stations.
- Portfolio accounting: match, city-tournament, and U.S.-tournament tests verify
  one-time capital per city, recurring event operations, and default exclusion
  of partial/unavailable access results.
- Local project-owned Streamlit preview: health check returned HTTP 200 at
  `http://127.0.0.1:8504` after the Decision Brief and Compare Cities integration.
- Screenshot record: failed because the in-app browser sandbox-policy handshake
  blocked localhost control. No desktop/narrow screenshot claim is made.
- Known release limitations: published GTFS does not include confirmed FIFA
  special-event overlays; 29 match records show zero scheduled half-mile
  capacity, 23 lack a stop-route/route-heat path, and three cities fail strict
  MRS Rice venue-coverage gates. Team/contact metadata and final desktop/narrow
  screenshot review remain outstanding.

This is a competition MVP validation record, not certification for operational
traffic management.

Run W6-owned checks from the repository root:

```powershell
uv run python -m pytest dashboard/tests/integration
uv run ruff check dashboard/tests/integration
git diff --check
```
