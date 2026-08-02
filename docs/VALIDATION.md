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
- The 2026-08-02 GTFS refresh produced four observed cities and two usable partial
  multi-agency cities. Three cities are outside the event window and Kansas City
  and Philadelphia failed; they remain unavailable. No legacy number became observed.

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

## Release evidence record — 2026-08-01

- Integration commits: `b008af7` (transportation bundle wiring) and `7ec3cad`
  (refreshed, per-match GTFS capacity evidence).
- Automated suite: `139 passed`.
- Ruff: passed for `dashboard`.
- Whitespace: `git diff --check` passed.
- Public cache validator: 78 schedule events, 11 walking city fixtures, 11 GTFS
  city records, five factor families; validator passed. The refreshed GTFS snapshot
  SHA-256 is `7d27c0f19982e667ce936ad107f5f19d7aaab118cecd33672b6be1be95ff1ded`;
  it is partial with 38 event-valid matches across four observed, two usable partial,
  and five unavailable cities.
- Streamlit AppTest: Executive, Explorer, and Methods & QA rendered without an
  exception; all 11 cities and named scenarios passed adapter checks.
- Local cache-only preview: HTTP 200 at `http://127.0.0.1:8502`.
- Screenshot record: not completed because the in-app browser policy blocked the
  visual connection. No screenshot claim is made.
- Known release failures: five cities lack event-valid GTFS evidence; walking
  layers are estimated schema fixtures rather than pinned OSM extracts; team/contact
  metadata is missing; final desktop/narrow screenshot review remains outstanding.
- Narrative reconciliation: completed against the current evidence-to-claim and
  supplemental-source registers. Capacity-qualified access gaps are withheld while
  GTFS is unavailable.

This is a competition MVP validation record, not certification for operational
traffic management.

Run W6-owned checks from the repository root:

```powershell
pytest dashboard/tests/integration
ruff check dashboard/tests/integration
git diff --check
```
