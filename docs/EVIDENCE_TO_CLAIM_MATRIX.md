# Evidence-to-claim matrix

This matrix is the presentation source of truth for contract `0.3.0`. A field
being defined does **not** mean that a current artifact contains eligible
evidence. Presenters must also check its status, source record, and release gate.

| Presentation metric | Contract fields | Permitted claim after release gate | Current integration status |
| --- | --- | --- | --- |
| Match and local kickoff | `MatchEvent.match_id`, `MatchEvent.kickoff_local`, `MatchEvent.venue` | Official schedule context from a pinned FIFA source | Contract ready; pinned schedule artifact pending integration |
| Attendance planning range | `MovementScenario.attendance_low`, `MovementScenario.attendance_base`, `MovementScenario.attendance_high` | Editable attendance scenario, not observed attendance | Contract ready; match-specific model pending integration |
| Hourly arrivals and departures | `MovementScenario.hourly_rows`, `MovementScenario.uncertainty_type` | Planning range by hour; “validated baseline” only after both holdouts pass | Contract ready; hourly model pending integration |
| Peak passenger demand | `AccessGapResult.peak_demand_per_hour` | Scenario peak passengers per hour | Contract ready; transportation calculation pending integration |
| Scheduled transit capacity | `AccessGapResult.transit_capacity_low`, `AccessGapResult.transit_capacity_base`, `AccessGapResult.transit_capacity_high` | Capacity range inferred from pinned schedules and explicit vehicle assumptions, not ridership | Contract ready; eligible GTFS evidence pending integration |
| Residual passenger gap | `AccessGapResult.residual_passengers` | Scenario passengers not covered by modeled scheduled capacity | Contract ready; access-gap model pending integration |
| Network walk distance | `AccessGapResult.network_walk_distance_m` | OSM-derived network distance with stated coverage | Contract ready; pinned network extracts pending integration |
| Post-match service span | `AccessGapResult.service_span_after_match_min` | Scheduled minutes of service after a match | Contract ready; GTFS event-window calculation pending integration |
| Route heat exposure | `AccessGapResult.route_heat_exposure_c` | Heat-exposure proxy along modeled access routes | Contract ready; route overlay pending integration |
| Gap resolved | `InterventionOutcome.gap_resolved_passengers` | Scenario passengers served by the package | Contract ready; intervention model pending integration |
| Venue-area vehicle trips | `InterventionOutcome.venue_vehicle_trips_low`, `InterventionOutcome.venue_vehicle_trips_base`, `InterventionOutcome.venue_vehicle_trips_high` | Scenario venue-area trip range, not measured traffic | Contract ready; intervention model pending integration |
| Net VMT | `InterventionOutcome.net_vmt_low`, `InterventionOutcome.net_vmt_base`, `InterventionOutcome.net_vmt_high` | Modeled VMT difference including added service and upstream park-and-ride travel | Contract ready; intervention model pending integration |
| Net emissions | `InterventionOutcome.net_co2e_kg_low`, `InterventionOutcome.net_co2e_kg_base`, `InterventionOutcome.net_co2e_kg_high` | Planning-range net CO2e using a pinned factor registry | Contract ready; factor registry and model pending integration |
| Heat exposure avoided | `InterventionOutcome.heat_exposure_person_hours_avoided` | Modeled person-hours of exposure avoided under stated uptake assumptions | Contract ready; pedestrian/cooling response pending integration |
| Package cost | `InterventionOutcome.cost_low`, `InterventionOutcome.cost_base`, `InterventionOutcome.cost_high` | Order-of-magnitude planning cost range | Contract ready; cited factors pending integration |
| Cost per passenger | `InvestmentRecommendation.cost_per_passenger` | Scenario cost per passenger served, shown with evidence quality | Contract ready; recommendation model pending integration |
| Implementation lead time | `InvestmentRecommendation.lead_time_band` | Planning lead-time band, not an agency commitment | Contract ready; recommendation model pending integration |
| Responsible actor | `InvestmentRecommendation.responsible_actor`, `InvestmentRecommendation.dependencies` | Candidate owner and dependencies for coordination | Contract ready; city-specific recommendations pending integration |

## Current claims that remain valid

- All six Rice datasets are canonical supplied evidence and retain provenance.
- Rice store visits and spend describe commercial activity, not match attendance.
- Contract `0.3.0` defines the release interfaces above.
- The current demand implementation remains a planning scenario because it did
  not beat its seasonal-naive comparator in both validation years.
- Current strict transit comparison is unavailable until eligible, pinned GTFS
  snapshots are integrated.

## Claim rule

A presentation metric is release-ready only when its contract field exists,
its artifact status is eligible, its source has a version and SHA-256 hash, and
the corresponding gate in `VALIDATION.md` passes. Otherwise, present it as a
pending capability or unavailable evidence—not as a result.
