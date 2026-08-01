# Mobility Readiness Model Card

## Intended use

The platform supports pre-event comparison and intervention discussion for FIFA
host-city planners, transit agencies, venue operators, and residents. It is not
a certified safety model, traffic forecast, or fan-origin model.

## Evidence dimensions

| Dimension | Primary evidence | Interpretation |
| --- | --- | --- |
| Transit | Pinned GTFS venue snapshot | Stops, routes, scheduled service, and distance to venue |
| Heat safety | Host-station weather | Event-window apparent heat and exposure |
| UHI safety | UHI points near venue | Localized heat-island intensity |
| Venue support | POI points near venue | Amenity-density proxy, not a sidewalk or accessibility audit |

## Score behavior

The headline score is a weighted average of the four dimensions. The default
profile is Balanced: Transit 35%, Heat 20%, UHI 15%, Venue Support 30%.

Observed and derived metrics participate in strict mode. Estimated metrics are
only included after the user opts in. Missing data is never silently converted
to an expert estimate.

## Demand model

The demand baseline uses 2022–2023 seasonal and weekday behavior and validates
against 2024 holdout dates where coverage permits. FIFA event bands are
scenario ranges. They should not be described as calibrated confidence
intervals unless the QA report demonstrates interval coverage.

## Traffic and emissions proxy

The intervention model converts user-selected shuttle and parking capacity into
potentially shifted passenger trips. Vehicle occupancy, trip distance, bus
capacity, uptake, and emissions factors are explicit editable assumptions. The
model does not observe road congestion, queue lengths, signal performance, or
actual fan mode choice.

## Known limitations

- Combined source markets require partial allocation.
- `CUSTOMER_HOME_CITY` describes general consumer mobility, not ticketed fans.
- GTFS availability and agency coverage vary by city.
- POI density does not establish safe or accessible pedestrian routes.
- Economic impact is contextual and should not be treated as causal attribution.
