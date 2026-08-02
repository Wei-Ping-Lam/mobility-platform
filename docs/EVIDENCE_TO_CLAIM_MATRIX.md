# Evidence-to-claim matrix

This matrix is the presentation source of truth for contract `0.3.0`. A field
being defined does **not** mean that a current artifact contains eligible
evidence. Presenters must also check its status, source record, and release gate.

| Presentation metric | Contract fields | Permitted claim after release gate | Current integration status |
| --- | --- | --- | --- |
| Match and local kickoff | `MatchEvent.match_id`, `MatchEvent.kickoff_local`, `MatchEvent.venue` | Official schedule context from a pinned FIFA source | Integrated: 78 observed US match records |
| Attendance planning range | `MovementScenario.attendance_low`, `MovementScenario.attendance_base`, `MovementScenario.attendance_high` | Editable attendance scenario, not observed attendance | Integrated as scenario evidence for every match |
| Hourly arrivals and departures | `MovementScenario.hourly_rows`, `MovementScenario.uncertainty_type` | Planning range by hour; “validated baseline” only after both holdouts pass | Integrated as planning scenario; both-year validation gate fails |
| Peak passenger demand | `AccessGapResult.peak_demand_per_hour` | Scenario peak passengers per hour | Integrated and visible for all 11 cities |
| Scheduled transit capacity | `AccessGapResult.transit_capacity_low`, `AccessGapResult.transit_capacity_base`, `AccessGapResult.transit_capacity_high` | Capacity range inferred from pinned schedules and explicit vehicle assumptions, not ridership | GTFS event evidence for 50 matches across eight cities; some remain partial after network/access composition |
| Residual passenger gap | `AccessGapResult.residual_passengers` | Scenario passengers not covered by modeled scheduled capacity | 29 matches pass the complete capacity-and-network gate; 21 remain partial and 28 unavailable |
| Network walk distance | `AccessGapResult.network_walk_distance_m` | OSM-derived network distance with stated coverage | Integrated where an event-relevant GTFS stop is eligible; isochrones remain available for all venues |
| Post-match service span | `AccessGapResult.service_span_after_match_min` | Scheduled minutes of service after a match | Integrated for 50 event-valid matches; unavailable elsewhere |
| Route heat exposure | `AccessGapResult.route_heat_exposure_c` | Heat-exposure proxy along modeled access routes | Integrated from Rice summer weather/UHI along valid OSM paths; unavailable without route/UHI coverage |
| Gap resolved | `InterventionOutcome.gap_resolved_passengers` | Scenario passengers served by the package | Integrated scenario model; recommendations remain partial without GTFS |
| Venue-area vehicle trips | `InterventionOutcome.venue_vehicle_trips_low`, `InterventionOutcome.venue_vehicle_trips_base`, `InterventionOutcome.venue_vehicle_trips_high` | Scenario venue-area trip range, not measured traffic | Integrated scenario range |
| Net VMT | `InterventionOutcome.net_vmt_low`, `InterventionOutcome.net_vmt_base`, `InterventionOutcome.net_vmt_high` | Modeled VMT difference including added service and upstream park-and-ride travel | Integrated with negative outcomes retained |
| Net emissions | `InterventionOutcome.net_co2e_kg_low`, `InterventionOutcome.net_co2e_kg_base`, `InterventionOutcome.net_co2e_kg_high` | Planning-range net CO2e using a pinned factor registry | Integrated as scenario/estimated planning range |
| Heat exposure avoided | `InterventionOutcome.heat_exposure_person_hours_avoided` | Modeled person-hours of exposure avoided under stated uptake assumptions | Integrated only when cooling changes the documented response |
| Package cost | `InterventionOutcome.cost_low`, `InterventionOutcome.cost_base`, `InterventionOutcome.cost_high` | Order-of-magnitude planning cost range | Integrated with cited scenario/estimated factors |
| Match-specific investment option | `InvestmentRecommendation.match_id`, `InvestmentRecommendation.intervention` | Pareto-efficient option for the identified match only | Integrated with strict city/match identity; recommendations never bleed across matches |
| Cost per passenger | `InvestmentRecommendation.cost_per_passenger` | Scenario cost per passenger served, shown with evidence quality | Integrated on Pareto screening options; status partial |
| Implementation lead time | `InvestmentRecommendation.lead_time_band` | Planning lead-time band, not an agency commitment | Integrated as planning band |
| Responsible actor | `InvestmentRecommendation.responsible_actor`, `InvestmentRecommendation.dependencies` | Candidate owner and dependencies for coordination | Integrated as candidate actor, not an assignment |

## Current claims that remain valid

- All six Rice datasets are canonical supplied evidence and retain provenance.
- Rice store visits and spend describe commercial activity, not match attendance.
- Contract `0.3.0` defines the release interfaces above.
- The current demand implementation remains a planning scenario because it did
  not beat its seasonal-naive comparator in both validation years.
- Strict transit comparison is available only for cities passing feed hash,
  required-file, and event-window gates; out-of-window matches remain unavailable.

## Claim rule

A presentation metric is release-ready only when its contract field exists,
its artifact status is eligible, its source has a version and SHA-256 hash, and
the corresponding gate in `VALIDATION.md` passes. Otherwise, present it as a
pending capability or unavailable evidence—not as a result.
