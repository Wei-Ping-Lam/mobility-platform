# Transportation model card

## Version and maturity

- Contract: `0.3.0`
- Intended release: competition-ready planning MVP
- Current state: Rice and public-source pipelines, contract-0.3 transportation
  models, and the Portfolio and City action plan workspaces are integrated and tested;
  Scenario Explorer and Methods are retained in code but deferred from public navigation
- Decision authority: advisory only; agencies retain operational and engineering
  responsibility

## Intended use

Host-city planners, transit agencies, venue operators, and residents can compare
match-specific access evidence and explore defined single-measure investments. The model is
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
| Published traffic plan | Content-hashed Dallas host-committee page | Source-audit reference for exact local facts | Retained for provenance; it does not override the normalized generated plan |
| Official-plan benchmark | Analyst-coded broad strategy families from 11 official host sources | Post-prediction family agreement | Calibration audit only; not an exact operating overlay or holdout accuracy |
| Models | All eligible layers plus editable assumptions | Hourly movement, broad visitor-flow mix, access gap, intervention outcomes, and time-phased traffic strategies | Scenario evidence unless validation says otherwise |

## Output semantics

- `MovementScenario` is low/base/high attendance and hourly flow with an explicit
  uncertainty type. The portfolio shows arrival and post-match departure peaks
  separately. It must be described as a planning scenario rather than a
  validated prediction.
- `VisitorFlowForecast` is a deterministic scenario artifact for all 78 official
  matches. It allocates attendance to four broad origin types and four broad
  venue-approach modes, then reports the reconciled low/base/high peak timing.
  Its domestic mix uses commercial customer origins only as a prior; its
  international share and mode response are explicit stage- and access-based
  assumptions. It does not infer exact visitor origins, destinations, routes,
  travel times, or observed mode choice.
- `AccessGapResult` reports scenario demand, scheduled capacity range, residual
  passengers, network walk distance, service span, and route heat exposure.
- `InterventionOutcome` reports gap resolved, venue-area vehicle trips, net VMT,
  net CO2e, heat exposure avoided, and costs as ranges where defined.
- `InvestmentRecommendation` identifies a candidate intervention, proposed scale, rationale,
  cost-effectiveness, lead-time band, responsible actor, dependencies, and
  status. It is not an agency commitment.
- `TrafficStrategyPlan` selects an evidence-responsive operating family from
  scheduled coverage, stop proximity, walking evidence, network scale, and
  regional-hub structure; translates the residual gap into low/base/high
  unconstrained bus equivalents; and orders five actions from pre-match through
  contingency. The official benchmark is compared only after prediction and
  does not override generated candidates, windows, actions, or controls.
- Operational and capital composites combine several measures only for sensitivity
  testing; they are not named investment recommendations.
- The Portfolio uses six objective tabs: Resilience, Visitor movement,
  First/last mile, Investments & transit, Traffic management, and Outcomes.
  All 11 cities remain visible in every comparison; exact values are disclosed
  without adding a portfolio map or city filter.
- Each City Action Plan provides two optional overlap maps. Venue access shows
  the half-mile screening boundary against pinned GTFS and walking geometry;
  operating overlap shows the selected anchor and the other retained GTFS
  candidates. Schematic links are not routing, capacity, or approval claims.
- The resilience comparison applies a common sensitivity of 10% more peak
  movement and 20% less scheduled capacity. It is a transparent physical stress
  test, not a disruption probability or reliability forecast.
- MRS is a secondary sensitivity-tested index, not the primary decision result.
- The portfolio does not rank cities by the added-frequency screen's cost per passenger.
  That ratio is useful for understanding one measure within an action plan, but the common
  six-departures-per-hour scale and national cost/capacity factors produce the same $11.31
  value across hosts, so it contains no cross-city decision information.
- The Portfolio chooses a priority screening measure from the evidence-qualified
  option set using explicit bottleneck rules. Zero serving capacity screens a
  shuttle; a long event-stop approach screens a shuttle connection; a hot
  documented approach can screen a cooled walking corridor; low coverage on an
  established route can screen added frequency. This is not an automatic optimum.
- Access, venue-area vehicle trips avoided, and net CO2e are compared separately
  in the Outcomes tab. They are scenario outputs, not observed mode shift,
  measured roadway congestion relief, or a certified emissions inventory.

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
- Broad visitor origin and mode allocations are not calibrated to FIFA ticketing,
  airport, hotel, mobile-device, parking, or passenger-count data. They are
  decision scenarios for comparing the scale and composition of host-city demand.
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
- Generated regional hubs do not establish special-event access, parking,
  loading, fleet, layover, staffing, emergency access, or control approval.
- A content-pinned Dallas plan is retained as source-audit evidence, but the
  normalized generated plan uses the same candidate-hub and action rules for
  every city. All 11 cities have reviewed broad strategy-family benchmarks;
  those labels do not make generated hubs, capacity, or controls official.
- Current family agreement is an in-sample calibration check. It is not a
  cross-city holdout result or evidence that exact operations were predicted.
- National cost and emissions factors do not replace local fleet, procurement,
  labor, design, or construction evidence.

## Responsible presentation

Use the exact metric names and conditions in `EVIDENCE_TO_CLAIM_MATRIX.md`.
Always disclose source status and at least one decision-relevant limitation.
