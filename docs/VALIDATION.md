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
- Eligible GTFS evidence is currently unavailable for strict transportation
  comparison. No legacy number becomes observed evidence.

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

- Executive answers where, why, candidate investment, modeled outcome, cost,
  lead time, and evidence quality without relying on MRS.
- Explorer supports match selection and Baseline, Operational Package, and
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

## Release evidence record

The integrator must append a dated report containing commit SHA, artifact
manifest hashes, source-refresh timestamps, test commands/results, 11-city UI
matrix, screenshots, known failures, and narrative reconciliation. Until that
record exists, supplemental capabilities remain “pending integration.”

Run W6-owned checks from the repository root:

```powershell
pytest dashboard/tests/integration
ruff check dashboard/tests/integration
git diff --check
```
