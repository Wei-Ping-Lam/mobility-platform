# Model equations

The code-owned registry is `dashboard/models/equations.py`. Stable IDs below
appear in Methods and scenario downloads so a reviewer can trace each
number to one definition. Multiplication and subtraction are evaluated
separately for low, base, and high cases where ranged factors apply.

## EQ-DEMAND-01 — hourly movement

```text
arrivals_h = attendance × normalized_arrival_share_h
```

Hourly shares reconcile to the selected attendance scenario. Attendance and the
arrival profile are planning scenarios, not observed ticket scans.

## EQ-VISITOR-FLOW-01 — World Cup attendee origin forecast

```text
origin_attendees_case = attendance_case × stage_origin_share_case
```

Every hosted match is allocated to host-market, nearby U.S., long-distance U.S.,
and international/unobserved origin types. The supplied spend-panel customer
origins shape only the relative domestic prior. International share is an explicit
low/base/high tournament-stage scenario. Neither input observes FIFA fans.

## EQ-CAPACITY-01 — scheduled transit capacity

```text
capacity_h = departures_h × vehicle_capacity × usable_load_factor
```

Departures come from event-valid GTFS. Capacity and load factors are planning
ranges. The result is potential throughput, not ridership or service reliability.

## EQ-MODE-SPLIT-01 — broad venue-access mode demand

```text
mode_attendees = origin_attendees × conditional_mode_share(
  transit_readiness,
  scheduled_peak_coverage,
  walking_path_evidence
)
```

Conditional shares cover scheduled transit, event shuttle/coach, private
vehicle/taxi, and walk/bike demand and reconcile to attendance. This is not
calibrated mode choice, delivered service, exact route assignment, travel time,
or observed roadway flow.

## EQ-GAP-01 — residual access gap

```text
gap_h = max(demand_h − scheduled_capacity_h, 0)
```

This is a passenger-per-hour planning gap, not roadway congestion or a measured
queue.

## EQ-TRAFFIC-SCALE-01 — unconstrained event-bus scale screen

```text
bus_equivalents_h = ceil(
  max(demand_h - scheduled_capacity_h, 0)
  / (bus_capacity * usable_load_factor)
)
```

The low case couples low demand with high usable bus capacity; the base case
uses base values; the high case couples high demand with low usable capacity.
The result is an order-of-magnitude residual-gap translation, not a fleet
recommendation. A base result above 60 buses/hour triggers a disclosed
single-hub review signal; that threshold is a project planning heuristic, not
an observed curb, layover, roadway, or dispatch limit.

## EQ-HUB-RANK-01 — regional GTFS candidate ranking

For each GTFS parent station more than 0.5 and no more than 40 miles from the
venue, with scheduled service active on at least one host match date:

```text
hub score = 8,000 × rail/ferry flag
          + 500 × route count
          + min(event-valid trip patterns, 999)
          + 10 × event-valid match dates
          − distance miles
```

Stations explicitly labeled “no service” are excluded. Candidates are sorted by
descending score, then distance and name; duplicate station names are removed
and at most eight are retained. The first retained station is the displayed
anchor. This ranks scheduled network connectivity only—not parking, platform,
curb, layover, staffing, ADA, emergency-access, or event-operations feasibility.

## EQ-RESILIENCE-01 — common access stress

```text
stressed_demand = demand_h × 1.10
stressed_capacity = capacity_h × 0.80
stress_coverage = stressed_capacity ÷ stressed_demand
stressed_gap = max(stressed_demand − stressed_capacity, 0)
```

The same sensitivity is applied to each representative match. Coverage is capped
at 100%. This is not a disruption probability, reliability forecast, or recovery
model.

## EQ-SPREAD-01 — effective arrival spreading

```text
requested_shift = peak × requested_share
behavior_limited_shift = requested_shift × eligible_share × compliance
shoulder_limit = peak × shoulder_capacity_share
shift_pph = min(behavior_limited_shift, shoulder_limit)
```

The shifted amount is moved to adjacent shoulder periods and total arrivals are
conserved. Only `min(residual_gap, shift_pph)` can receive access-gap credit.
No emissions or vehicle-trip credit is assigned. Because response and curb
capacity are unobserved, this measure is an exploratory sensitivity.

## EQ-INTERVENTION-01 — peak gap resolved

```text
resolved = min(residual_gap, physical_capacity_added + feasible_arrival_shift)
```

Physical capacity includes shuttle, added transit, park-and-ride feeder, bike,
and eligible walking uptake. Potential throughput is not observed mode shift.

## EQ-PARK-RIDE-01 — park-and-ride throughput

```text
park_pph = min(
  space_passengers / arrival_hours,
  feeder_departures_h × passengers_per_bus × usable_load_factor
)
```

Parking spaces do not create passenger throughput by themselves. The model
requires explicit feeder departures, caps passengers at the lower of parking
and feeder capacity, includes feeder VMT, and prices scheduled feeder service
as event bus-hours.

## EQ-VMT-01 — net vehicle-miles avoided

```text
net_VMT = avoided_private_VMT − added_service_VMT
```

Park-and-ride retains upstream driving and avoids only the venue-area leg.
Shuttle, transit, and feeder operating mileage is deducted.

## EQ-CO2-01 — net CO2e avoided

```text
net_CO2e = avoided_private_VMT × private_factor
           − added_service_VMT × service_factor
```

Negative values are retained. The factors are planning ranges, not a local MOVES
inventory.

## EQ-COST-01 — total planning cost

```text
total_cost = one_time_capital + per_event_operations
```

Total cost is never replaced by an amortized value in the interface.

## EQ-COST-02 — comparison cost per passenger

```text
comparison_cost = per_event_operations + one_time_capital ÷ reusable_event_uses
comparison_CPP = comparison_cost ÷ peak_gap_resolved
```

This puts reusable and operating measures on a common screening basis while
retaining total cost. Event uses are explicit scenario factors.

## EQ-PARETO-01 — nondominated option set

Option A dominates B only when A is no worse on all of the following and better
on at least one:

- peak gap resolved;
- net CO2e avoided;
- comparison cost per passenger;
- implementation lead-time rank; and
- heat-exposure person-hours avoided.

An exploratory option cannot dominate an evidence-qualified option. Frontier
membership means only that a tradeoff remains; it is not a selected optimum,
funding recommendation, or agency approval.
