# App Review and Estimate Audit

Reviewed September 15, 2026. Scope: Portfolio, all 11 City Action Plans, action-impact calculations, and capital alternatives.

## Corrections

- Replaced pooled fractional bus trips with per-vehicle delivery schedules. A staged bus can deliver passengers before its empty return finishes; the return still incurs full mileage and operating time.
- Included a separate 10% depot-mileage allowance and one paid setup hour per active bus. Paid service covers both event windows and any later return. These are explicit planning assumptions, not operator quotes.
- Kept stated travel-credit face values fixed across low/base/high scope cases.
- Replaced the action model's universal electric-bus emissions discount with regional electricity accounting, including charging and grid-delivery losses.
- Added a fixed-scope CO2e factor-sensitivity range. Negative results are retained, not clipped or redesigned automatically to meet a positive target.
- Capital fleets now reserve vehicles and test 25% slower event cycles. Passenger ranges are potential service capacity at assumed loads, not a forecast of demand or newly attracted riders.
- Separated fleet purchases, charging/depot allowances, fleet/infrastructure contingency, and corridor costs. Fleet contingency is not added again to the corridor risk allowance.
- Fixed capital cards incorrectly labeled unavailable, stale references to removed comparison/traffic sections, and the transit-access profile's incorrect weight description.

## Source Basis

Electric bus operating emissions use vehicle kWh/mile divided by charging efficiency, multiplied by regional kg CO2e/kWh, adjusted for grid delivery losses.

- [EPA eGRID2023 revision 2](https://www.epa.gov/egrid/summary-data): regional annual-average electricity CO2e factors. Service-area assignments are proxies until actual charging depots and electricity suppliers are identified.
- [CARB Appendix I](https://ww2.arb.ca.gov/sites/default/files/barcu/regact/2018/ict2018/appi.pdf): 2.1 kWh/mile and 90% charging-efficiency planning assumptions.
- [NREL LA100 Chapter 3](https://docs.nlr.gov/docs/fy21osti/79444-3.pdf): 2.84 kWh/mile higher-use reference. The 1.8 kWh/mile lower case and 5% grid-delivery loss remain analyst assumptions.
- [California State Auditor](https://www.auditor.ca.gov/reports/2025-120/): battery-electric bus purchase range of $1.3-$1.7 million. This is not a Boston motorcoach quote.
- [FTA fleet-transition context](https://www.transit.dot.gov/sites/fta.dot.gov/files/2021-01/FTA-Report-No-0182.pdf): reserve-fleet considerations. The model's 20% spare-to-active planning ratio is not a finding that a fleet is compliant or sufficiently reliable.
- [Raleigh Northern BRT study, Table 12](https://cityofraleigh0drupal.blob.core.usgovcloudapi.net/drupal-prod/COR28/northern-bus-rapid-transit-major-investment-study-spring26.pdf): conceptual corridor cost context. The app's separate $10-$25 million/mile corridor allowance remains an analyst scenario, not a directly transferred project estimate.

## Remaining Limits

- Beneficiary percentages, car-to-transit shifts, route lengths, loading and staffing budgets are not locally calibrated. More precise arithmetic does not turn these into validated forecasts.
- Houston, Miami and Kansas City can have negative savings under adverse factors even while their base cases remain positive. Procurement and dispatch should be conditional on measured loads, actual replacement service and charging performance.
- CO2e estimates compare operating emissions, not full lifecycle impacts. They omit vehicle manufacture, construction and upstream fuel supply chains. Existing-rail shifts assume spare capacity and omit marginal passenger energy.
- Boston, Dallas, Kansas City and Los Angeles require equivalent conventional trips to be displaced. Los Angeles's actual vehicle/fuel mix matters; its renewable-natural-gas supply chain is not evaluated by the generic conventional-vehicle proxy.
- Capital capacity assumes available drivers, loading bays, battery range and charging between service windows. Long-distance electric coaches need vehicle-specific validation.
- Costs exclude operator-required mid-match standby, major land acquisition, financing, future price escalation and lifecycle replacement. Capital ranges are reference-price concepts, not bids or funded projects.
- Road maps show selected documented 2026 event-plan segments, not live closures or a comprehensive citywide traffic feed.

## Verification

All 420 tests passed, including model/accounting tests and all-city/all-tab Streamlit smoke tests. Ruff, Python compilation and git diff whitespace checks passed. Real Chrome checks at 1440px desktop and 390px mobile widths reported no JavaScript exceptions or overflowing metric values. Screenshots confirmed readable capital/impact cards and rendered red road closures.
