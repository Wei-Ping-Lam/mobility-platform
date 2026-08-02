# Mobility Readiness Model Card

## Intended use

The platform supports pre-event comparison and intervention discussion for FIFA
host-city planners, transit agencies, venue operators, and residents. It is not
a certified safety model, traffic forecast, or fan-origin model.

## Evidence dimensions

| Dimension | Primary evidence | Interpretation |
| --- | --- | --- |
| Transit | Pinned GTFS venue snapshot | Stops, routes, scheduled service, calendar validity, event-window service, and venue distance |
| Heat safety | Host-station weather | Event-window apparent heat and exposure |
| UHI safety | UHI points near venue | Localized heat-island intensity |
| Venue support | POI points near venue | Amenity-density proxy, not a sidewalk or accessibility audit |

## Score behavior

The headline score is a weighted average of the four dimensions. The dashboard
defaults to the supplied-data lens: Heat 35%, UHI 25%, Venue Support 40%, and
Transit 0%. This supports a comparison from the Rice collection while the UI
states that transit has been excluded. The Balanced profile remains available:
Transit 35%, Heat 20%, UHI 15%, Venue Support 30%.

Observed and derived metrics participate in strict mode. Estimated metrics are
only included after the user opts in. Missing data is never silently converted
to an expert estimate. A partial weighted-available MRS remains visible for
auditability, but the Executive `rankable` flag is false unless every
non-zero-weight core dimension is evidence-eligible.

## Demand model

The demand baseline uses 2022-2023 seasonal and weekday behavior, with rolling
2023 and 2024 holdouts compared with a 364-day seasonal-naive comparator where
coverage permits. FIFA event bands are scenario ranges. They should not be
described as calibrated confidence intervals unless the QA report demonstrates
interval coverage.

## Traffic and emissions proxy

The intervention model converts user-selected shuttle and parking capacity into
potentially shifted passenger trips. Vehicle occupancy, trip distance, bus
capacity, uptake, and emissions factors are explicit editable assumptions. The
model does not observe road congestion, queue lengths, signal performance, or
actual fan mode choice.

## Economic activity scenario

The economic range uses the median observed daily commercial spend from
2022-2024 and explicit 2%/5%/10% low/base/high uplift assumptions over the event
window. It is a scenario for planning discussion, not causal attribution,
stadium attendance, or a local-GDP forecast.

## Known limitations

- Combined source markets require partial allocation.
- The supplied-data lens is not a complete transportation-readiness score
  because it deliberately excludes transit service evidence.
- `CUSTOMER_HOME_CITY` describes general consumer mobility, not ticketed fans.
- GTFS availability and agency coverage vary by city.
- POI density does not establish safe or accessible pedestrian routes.
- The platform does not measure roadway congestion, ridership, parking occupancy,
  signal performance, crashes, or pedestrian counts.
- The supplied datasets are noisy educational data and should not be treated as
  certified real-world assessments.
