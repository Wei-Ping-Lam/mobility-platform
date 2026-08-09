# Evidence-to-claim matrix

This matrix is the presentation source of truth for contract `0.3.0`. A field
being defined does **not** mean that a current artifact contains eligible
evidence. Presenters must also check its status, source record, and release gate.

| Presentation metric | Contract fields | Permitted claim after release gate | Current integration status |
| --- | --- | --- | --- |
| Match and local kickoff | `MatchEvent.match_id`, `MatchEvent.kickoff_local`, `MatchEvent.venue` | Official schedule context from a pinned FIFA source | Integrated: 78 observed US match records |
| Attendance planning range | `MovementScenario.attendance_low`, `MovementScenario.attendance_base`, `MovementScenario.attendance_high` | Editable attendance scenario, not observed attendance | Integrated as scenario evidence for every match |
| Broad visitor-flow scenario | `visitor_flow_forecasts[*]` scenario artifact: origin, mode, attendance, and peak rows | Stage-conditioned scenario forecast of four broad origin types and four venue-approach modes; not observed or calibrated fan behavior | Integrated for all 78 matches; every case reconciles to attendance, commercial origins remain a context prior, and international share is an explicit stage assumption |
| Exact visitor origins, OD pairs, routes, and travel times | No current field | No positive prediction claim is permitted | Not implemented; the platform does not infer exact visitor locations or network assignments |
| Hourly arrivals and departures | `MovementScenario.hourly_rows`, `MovementScenario.uncertainty_type` | Planning range by hour; “validated baseline” only after both holdouts pass | Integrated as planning scenario; both-year validation gate fails |
| Peak passenger demand | `AccessGapResult.peak_demand_per_hour` | Scenario peak passengers per hour | Integrated and visible for all 11 cities |
| Scheduled transit capacity | `AccessGapResult.transit_capacity_low`, `AccessGapResult.transit_capacity_base`, `AccessGapResult.transit_capacity_high` | Capacity range inferred from pinned schedules and explicit vehicle assumptions, not ridership | Event-valid GTFS evidence for all 78 matches; 29 have observed zero scheduled half-mile capacity |
| Residual passenger gap | `AccessGapResult.residual_passengers`, `AccessGapResult.capacity_qualified` | Scenario passengers not covered by modeled scheduled capacity | All 78 are capacity-qualified; 55 have complete modeled route/heat components and 23 remain partial for those components |
| Common resilience stress | Portfolio stress fields derived from peak demand and scheduled capacity | Scheduled coverage after 10% more demand and 20% less capacity; sensitivity only | Integrated for representative matches; no probability or recovery claim |
| Network walk distance | `AccessGapResult.network_walk_distance_m` | OSM-derived network distance with stated coverage | Integrated where an event-relevant GTFS stop is eligible; isochrones remain available for all venues |
| Post-match service span | `AccessGapResult.service_span_after_match_min` | Scheduled minutes of service after a match | Integrated for all 78 event-valid match records; it does not guarantee delivered special-event service |
| Route heat exposure | `AccessGapResult.route_heat_exposure_c` | Heat-exposure proxy along modeled access routes | Integrated from Rice summer weather/UHI along valid OSM paths; unavailable without route/UHI coverage |
| Gap resolved | `InterventionOutcome.gap_resolved_passengers` | Scenario passengers served by the package | Integrated scenario model; recommendations remain partial without GTFS |
| Venue-area vehicle trips | `InterventionOutcome.venue_vehicle_trips_low`, `InterventionOutcome.venue_vehicle_trips_base`, `InterventionOutcome.venue_vehicle_trips_high` | Scenario venue-area trip range, not measured traffic | Integrated scenario range |
| Net VMT | `InterventionOutcome.net_vmt_low`, `InterventionOutcome.net_vmt_base`, `InterventionOutcome.net_vmt_high` | Modeled VMT difference including added service and upstream park-and-ride travel | Integrated with negative outcomes retained |
| Net emissions | `InterventionOutcome.net_co2e_kg_low`, `InterventionOutcome.net_co2e_kg_base`, `InterventionOutcome.net_co2e_kg_high` | Planning-range net CO2e using a pinned factor registry | Integrated as scenario/estimated planning range |
| Heat exposure avoided | `InterventionOutcome.heat_exposure_person_hours_avoided` | Modeled person-hours of exposure avoided under stated uptake assumptions | Integrated only when cooling changes the documented response |
| Effective arrival shift | `InterventionOutcome.arrival_shifted_pph_low`, `InterventionOutcome.arrival_shifted_pph_base`, `InterventionOutcome.arrival_shifted_pph_high` | Requested shift reduced by eligible share, compliance, and shoulder capacity; total flow conserved | Exploratory sensitivity because response and curb capacity are unobserved |
| Package cost | `InterventionOutcome.cost_low`, `InterventionOutcome.cost_base`, `InterventionOutcome.cost_high`, `InterventionOutcome.capital_cost_base`, `InterventionOutcome.operating_cost_base` | Total order-of-magnitude planning cost with capital and operations separated | Integrated with cited scenario/estimated factors |
| Match-specific investment option | `InvestmentRecommendation.match_id`, `InvestmentRecommendation.intervention`, `InvestmentRecommendation.scope`, `InvestmentRecommendation.evidence_qualified` | Defined nondominated option for the identified match; evidence-qualified and exploratory classes remain separate | Integrated with strict city/match identity and explicit candidate scale; no option is labeled an optimum |
| Portfolio priority screen | Representative-match access evidence plus evidence-qualified `InvestmentRecommendation` rows | Bottleneck-matched measure to validate first, with reason, owner, cost, lead time, and dependencies | Integrated; zero service cannot qualify added frequency without an established route |
| Comparison cost per passenger | `InvestmentRecommendation.comparison_cost_base`, `InvestmentRecommendation.cost_per_passenger`, `InvestmentRecommendation.cost_basis` | Per-event operations plus reusable capital per assumed event use, divided by resolved gap | Total project/event cost remains visible; reuse is an explicit scenario assumption |
| Evidence quality | `InvestmentRecommendation.evidence_quality`, `InvestmentRecommendation.evidence_reason` | Written evidence gate and limitation for each option | Arrival management, park-and-ride, and bike hubs remain exploratory until their required local evidence is supplied |
| Implementation lead time | `InvestmentRecommendation.lead_time_band` | Planning lead-time band, not an agency commitment | Integrated as planning band |
| Responsible actor | `InvestmentRecommendation.responsible_actor`, `InvestmentRecommendation.dependencies` | Candidate owner and dependencies for coordination | Integrated as candidate actor, not an assignment |
| Official operational benchmark | Operational snapshot `metrics[*]` and `event_records[*]` with source IDs, locators, granularity, and non-use limits | Source-attributed post-event aggregate or match record for exactly the stated scope and unit | 33 benchmarks across all 11 cities plus 13 match records; displayed separately and prohibited from silently calibrating match-hour scenarios |
| Venue-proximate weather supplement | Environment snapshot `weather_daily[*]` | June-July heat context from NOAA Global Hourly after station-distance and daily-coverage gates | Miami and New York/New Jersey only; temperature/dew point derive daily relative humidity and do not measure venue microclimate |
| Boston surface UHI supplement | Environment snapshot `uhi_city[*]` | Landsat surface-temperature anomaly near the venue | Five cloud-masked scenes from 2022-2024; not air temperature, shade, physiological exposure, or an accessibility audit |

## Current claims that remain valid

- All six Rice datasets are canonical supplied evidence and retain provenance.
- Rice store visits and spend describe commercial activity, not match attendance.
- Contract `0.3.0` defines the release interfaces above.
- The current demand implementation remains a planning scenario because it did
  not beat its seasonal-naive comparator in both validation years.
- Strict transit comparison is available only for cities passing feed hash,
  required-file, and event-window gates; out-of-window matches remain unavailable.
- Official post-event aggregates can benchmark scale and throughput only within
  their documented granularity. They do not establish match-hour demand,
  stadium attendance, causal impact, or mode share unless the source explicitly
  reports that field.

## Claim rule

A presentation metric is release-ready only when its contract field exists,
its artifact status is eligible, its source has a version and SHA-256 hash, and
the corresponding gate in `VALIDATION.md` passes. Otherwise, present it as a
pending capability or unavailable evidence—not as a result.
