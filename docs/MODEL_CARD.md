# Transportation model card

## Version and maturity

- Contract: `0.3.0`
- Intended release: competition-ready planning MVP
- Current state: Rice and public-source pipelines, contract-0.3 transportation
  models, and all four dashboard workspaces are integrated and tested
- Decision authority: advisory only; agencies retain operational and engineering
  responsibility

## Intended use

Host-city planners, transit agencies, venue operators, and residents can compare
match-specific access evidence and explore transportation packages. The model is
appropriate for screening, scenario comparison, evidence-gap discovery, and
order-of-magnitude planning.

It is not an operational traffic model, ridership forecast, accessibility or
safety audit, certified emissions inventory, engineering cost estimate, or
causal evaluation.

## Inputs and outputs

| Layer | Inputs | Outputs | Evidence interpretation |
| --- | --- | --- | --- |
| Supplied context | Six `Rice WC Hack/` datasets | Activity, weather, UHI, POI, origin, and spending summaries | Noisy educational evidence; activity is not attendance |
| Match | Pinned official FIFA schedule | Match, venue, local kickoff, stage, capacity | Official context after source gate passes |
| Transit | Pinned official agency GTFS | Departures, service span, route/stop evidence, capacity range | Scheduled supply, not observed operations |
| Walking | Pinned OSM network | Network distance, isochrones, detour, tag coverage | Planning network; missing tags remain unknown |
| Factors | Pinned EPA/FTA/FHWA references | Emissions and cost ranges | National/order-of-magnitude assumptions |
| Models | All eligible layers plus editable assumptions | Hourly movement, access gap, package outcomes, tradeoffs | Scenario evidence unless validation says otherwise |

## Output semantics

- `MovementScenario` is low/base/high attendance and hourly flow with an explicit
  uncertainty type.
- `AccessGapResult` reports scenario demand, scheduled capacity range, residual
  passengers, network walk distance, service span, and route heat exposure.
- `InterventionOutcome` reports gap resolved, venue-area vehicle trips, net VMT,
  net CO2e, heat exposure avoided, and costs as ranges where defined.
- `InvestmentRecommendation` identifies a candidate intervention, rationale,
  cost-effectiveness, lead-time band, responsible actor, dependencies, and
  status. It is not an agency commitment.
- MRS is a secondary sensitivity-tested index, not the primary decision result.

## Validation and uncertainty

Planning ranges reflect assumptions and factor ranges; they are not confidence
intervals unless empirical coverage is separately demonstrated. Baseline demand
language becomes “validated” only after both annual holdouts beat the
seasonal-naive comparator. Monotonic, reconciliation, physical-accounting,
cross-city differentiation, source-integrity, and download-reproduction gates
are defined in `VALIDATION.md`.

## Current evidence limitations

- GTFS feed evidence is observed for all 11 cities and event-valid for all 78
  matches. Twenty-nine matches have observed zero scheduled half-mile capacity;
  published GTFS does not establish whether special-event overlays will run.
- The present event-demand band is generic and did not beat its comparator in
  both validation years; it remains a planning scenario.
- Boston lacks eligible two-mile Rice UHI coverage; Miami and New York/New
  Jersey use weather stations beyond the current 30-mile evidence rule.
- Dallas/Houston and Los Angeles/San Francisco have combined supplied markets
  requiring visible partial allocation.
- Spatial jitter in supplied data limits parcel- or route-level interpretation.
- OSM tag presence cannot establish sidewalk condition, crossing safety, or ADA
  compliance.
- Five-mile OSM isochrones cover all venues, but event-relevant stop paths are
  unavailable for Boston, Dallas, and Miami; tag completeness varies by city.
- GTFS cannot establish actual service delivery, ridership, crowding, or delay.
- National cost and emissions factors do not replace local fleet, procurement,
  labor, design, or construction evidence.

## Responsible presentation

Use the exact metric names and conditions in `EVIDENCE_TO_CLAIM_MATRIX.md`.
Always disclose source status and at least one decision-relevant limitation.
