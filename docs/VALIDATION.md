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
- The 2026-08-02 GTFS refresh produced six observed cities and two usable partial
  multi-agency cities. Three cities remain outside the event window. Pinned,
  hash-checked archives repaired Kansas City and Philadelphia; no legacy number
  became observed.

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
- Automated suite: `168 passed`; Ruff passes. Whitespace is checked separately.
- Public cache validator: 78 schedule events, 20 planning factors, 11 GTFS city
  records, and 11 graph-derived walking records; validator passed.
- GTFS artifact SHA-256:
  `d58a87de35e7f3572c8aee59b204945b51b3be7488fdf2071860375ae3667e50`.
  It contains 50 event-valid matches, 2,698 venue-area stops, and 138 bounded
  route shapes across six observed and five partial cities.
- OSM artifact SHA-256:
  `8a5ed024ecc9826778bf136aeedf6309820924768befab44c0266ce9e446b1f9`.
  All 11 venues have five-mile graph-derived isochrones; seven have a network
  path to an event-relevant GTFS stop.
- Factor artifact SHA-256:
  `f36cba57ede7b6c7dfb720c492ee584545b46912e0cac7da4d7337c5bdb1bbd6`.
  Production composition fails on missing/incomplete factors and every outcome
  includes this hash in its assumptions.
- Streamlit AppTest: Decision Brief, Compare Cities, City & Match, and Methods & QA
  render without an exception. All 78 movement timelines and before/after tables
  pass nonempty, reconciliation, and peak-reduction checks.
- Recommendation identity: all 231 Pareto records retain an exact `match_id`;
  each match renders only its own two or three nondominated options.
- All-city comparison: five cities are strictly rankable under the default
  balanced profile; all 11 remain visible in the bounded screening view.
- Portfolio accounting: match, city-tournament, and U.S.-tournament tests verify
  one-time capital per city, recurring event operations, and default exclusion
  of partial/unavailable access results.
- Local project-owned Streamlit preview: health check returned HTTP 200 at
  `http://127.0.0.1:8504` after the Decision Brief and Compare Cities integration.
- Screenshot record: failed because the in-app browser sandbox-policy handshake
  blocked localhost control. No desktop/narrow screenshot claim is made.
- Known release failures: 28 matches still lack event-valid service evidence;
  another 21 access results remain partial after service/network composition;
  team/contact metadata and final
  desktop/narrow screenshot review remain outstanding.

This is a competition MVP validation record, not certification for operational
traffic management.

Run W6-owned checks from the repository root:

```powershell
uv run python -m pytest dashboard/tests/integration
uv run ruff check dashboard/tests/integration
git diff --check
```
