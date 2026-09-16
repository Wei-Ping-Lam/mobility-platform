# FIFA 2026 Host City Mobility Readiness
## Narrative: Methods, Results, and Proposed Solutions

**Track 1: Transportation & Access**<br>
**Scope:** All 11 U.S. host cities and 78 U.S. matches in the pinned FIFA 2026 schedule.

## Project Purpose

Large events concentrate thousands of people around venues within a short period. A city may have extensive transportation infrastructure yet still face difficult transfers, limited pedestrian access, expensive event services, or a heavy dependence on private vehicles. The challenge is not simply moving more people: it is making event access more sustainable while using existing resources effectively.

Our solution is an interactive mobility-readiness platform that connects a cross-city assessment to specific, locally relevant actions. It helps city planners, transit agencies, venue operators, and event organizers answer three questions: Where are the access weaknesses? What visitor demand should we plan for? Which interventions could improve access and reduce transportation emissions?

The platform moves users from a Portfolio view of all U.S. hosts to a City Action Plan containing the local problem, documented transportation conditions, a recommended first action, and quantified planning estimates. Its contribution is the connection between evidence, diagnosis, and action, rather than a ranking alone.

## Methods

### Evidence and Spatial Analysis

The analysis combines the six supplied Rice datasets with a pinned FIFA match schedule, agency General Transit Feed Specification (GTFS) data, OpenStreetMap networks, and cited transportation plans. These inputs provide venue context, scheduled service, walking connections, parking facilities, and documented event strategies. Weather and urban-heat evidence support the heat-safety assessment, with targeted NOAA and Landsat supplements where the supplied evidence required replacement.

Transit analysis checks scheduled service against event dates and time windows. Network-based walking analysis distinguishes actual mapped connections from straight-line proximity. Published-service evidence is considered alongside nearby stops because a dedicated stadium train or remote transfer service may provide meaningful access even when a radius-based measure misses it. Maps also show selected documented traffic-control segments where usable geometry is available.

Source records and evidence statuses distinguish observed inputs, derived measures, estimates, and unavailable information. Scheduled departures are not treated as observed ridership, and mapped walking paths are not certified safe or accessible routes. The maps use pinned evidence rather than live operating feeds.

### Readiness, Access, and Sustainability

The balanced readiness index combines four normalized components: first/last-mile access (30%), traffic management (30%), heat safety (25%), and venue support (15%). Users can change the comparison weights to explore different priorities. These weights are explicit planning judgments, not statistically fitted measures of event success.

Access and sustainability are deliberately evaluated separately. The access score combines 75% transit-access evidence with 25% parking-facility density. Within transit access, the weights are transit-stop density (30%), event-window frequency (20%), dedicated-service evidence (35%), and pedestrian infrastructure (15%). The separate sustainability score combines lower parking density (50%), fleet-electrification evidence (30%), and pedestrian infrastructure (20%). Where permitted by the model's evidence rules, missing subcomponents are excluded and available weights are renormalized.

This distinction matters: parking can support practical venue access while also indicating car-dependent development. Parking-facility density is a proxy, not a count of available parking spaces, and the sustainability score is not a measured emissions inventory. The scores support screening; the underlying evidence and physical quantities remain essential to interpreting them.

### Visitor Movement Scenarios

Match attendance is modeled at 85%, 95%, and 100% of venue capacity. Hourly arrival and departure profiles are anchored to local kickoff times and conserve attendance within each direction. The peak comparison uses each city's match with the greatest modeled base non-host-market demand; the hourly curves average across that city's hosted matches.

The shaded bands show attendance-scenario uncertainty, not statistical confidence intervals. Cities share a planning timing profile, so differences in curve height primarily reflect modeled attendance rather than locally calibrated travel behavior. Broad attendee-origin and transportation-mode allocations use tournament stage, commercial-origin context, and transportation evidence. They are scenario estimates, not ticket-holder observations or detailed route predictions. Tournament attendance totals represent attendee-visits across matches, not unique individuals.

### Intervention and Emissions Accounting

Recommended actions are translated into defined operating assumptions. Bus scenarios account for vehicles, passenger capacity, load factors, event-window deliveries, full return trips, depot mileage, and paid operating time. Passenger estimates are demand-capped, and the same passenger is not counted twice for traveling to and from a match.

Net operating CO2e avoided equals avoided private-vehicle emissions plus displaced conventional-service emissions, minus emissions from the replacement or additional service. Electric-bus calculations use regional EPA electricity factors, vehicle energy consumption, charging efficiency, and grid-delivery losses. Vehicle-mile savings are calculated separately: electrifying an existing trip can reduce emissions without eliminating that trip.

Costs distinguish recurring event operations from upfront capital. Low/base/high cases explore scope assumptions, while a separate fixed-scope emissions range tests factor sensitivity. These are planning estimates rather than validated forecasts, procurement quotes, or full lifecycle assessments.

## Results

### Strong Access Does Not Necessarily Mean Sustainable Access

Under the current balanced weights, Seattle scores 84.4/100 for readiness, with access of 98.9 and sustainability of 97.0. Atlanta scores 75.6 for readiness and 88.0 for access, but only 32.2 for sustainability.

Atlanta is therefore an important outlier: improving its outcome does not necessarily require building another major transit connection. Its profile points toward using existing transit more effectively and reducing private-vehicle dependence. The difference between Atlanta and Seattle demonstrates why an access ranking alone would miss an important sustainability opportunity.

### City-by-City Findings and Recommended Actions

The table summarizes each host's diagnosis and proposed response in the current City Action Plan, based on the app's pinned evidence. These are priorities for local validation, not implemented projects or guaranteed benefits.

| Host city | Main finding or access challenge | Recommended response |
| --- | --- | --- |
| Atlanta | Strong MARTA access contrasts with abundant nearby parking and a weaker sustainability score. | Manage event-day parking prices and restrictions to encourage existing rail use rather than add parking capacity. |
| Boston | Car-free access to Foxborough is costly, requires advance planning, and remains exposed to regional road congestion. | Support fares on existing stadium trains and express buses; replace conventional express buses with electric vehicles where range and charging permit. |
| Dallas | The existing rail-to-bus connection provides access, but reactive overflow dispatch risks queues. | Pre-position electric overflow buses at Victory and Fort Worth Central, replacing equivalent conventional trips and sizing departures to bookings. |
| Houston | Long walking distances can deter visitors despite corridor shade and water amenities. | Offer a reserved electric shuttle for the final one to two miles near NRG, with dispatch conditional on sufficient bookings and car-trip replacement. |
| Kansas City | Restricted stadium entrance operations create an access bottleneck beyond the shuttle network itself. | Open more entrances with traffic marshals and replace four conventional Stadium Direct buses with electric buses on the same booked trips. |
| Los Angeles | Reliable bus connections to the Metro K and C Lines are central to venue access. | Enforce connector bus lanes and signal priority, paired with six electric buses replacing conventional connector trips. |
| Miami | A venue without direct rail access depends on its hub-and-shuttle network, especially during concentrated post-match departures. | Pre-stage electric buses at the four existing hubs; tie added departures to reservations and enough displaced car travel to reduce emissions. |
| New York/New Jersey | Strong dedicated rail service coexists with constrained sanctioned pedestrian access. | Improve and widen the sanctioned path from the rideshare lot, subject to accessibility and security review, rather than default to more rail capacity. |
| Philadelphia | Strong rail access concentrates post-match passengers at the stadium-complex station. | Combine platform crowd management and signage with targeted rail credits, offered only after confirming spare train capacity. |
| San Francisco Bay Area | Event-day trail closures create localized walking and cycling detours; post-match transfers also warrant operational attention. | Improve approved-detour wayfinding and crossings, and coordinate transfers at Mountain View and Milpitas using measured queues and missed connections. Only detour improvements are currently quantified. |
| Seattle | Strong transit and walking access leave an opportunity to reduce remaining discretionary car trips. | Offer targeted rail-travel credits and station guidance, using confirmed spare capacity rather than adding vehicle service. |

Across the hosts, the common principle is to strengthen existing services before duplicating them. The sustainability mechanism differs by city: shifting trips away from cars, replacing higher-emission vehicles, or making existing transit and pedestrian connections easier to use. Operational improvements alone do not establish a CO2e saving; the quantified cases must demonstrate displaced emissions under their stated assumptions.

### Different Actions Produce Different Kinds of Benefits

The following examples were reproduced from the current model using base assumptions for the identified matches. They describe proposed actions, not benefits already achieved.

| City and match | Quantified action scope | Passengers addressed per match | Net operating CO2e avoided per match | Estimated first-event cost |
| --- | --- | ---: | ---: | ---: |
| Dallas, M011 | Electric buses replacing equivalent conventional overflow service | 540 | 1.23 metric tonnes | $14,096 |
| Boston, M005 | Electric replacement express service with a $20-per-rider travel credit | 405 | 2.59 metric tonnes | $28,244 |
| Houston, M010 | Electric last-mile service with an assumed 40% car-trip replacement share | 1,080 | 0.078 metric tonnes | $7,394 |

Dallas illustrates a focused, incremental intervention: retain the transfer function and reduce the emissions of the vehicles providing it. The estimate credits no vehicle-mile reduction because equivalent conventional trips are replaced rather than removed. Boston's quantified package similarly improves an existing service; it does not assume that all broader affordability recommendations have been implemented.

Houston illustrates the importance of testing a sustainability claim. Its base case is positive, but its fixed-scope factor range runs from approximately -0.116 to +0.234 metric tonnes avoided per match. Additional service is not automatically lower-carbon: occupancy, displaced car travel, and electricity use determine the result. Miami and Kansas City also have adverse sensitivity cases with negative savings. Positive base cases therefore identify candidates for validation, not guaranteed outcomes.

Passengers addressed include service users or explicitly assumed beneficiaries of an action. They should not be interpreted universally as new transit riders, people diverted from cars, or an access gap fully resolved.

## Proposed Solution and Implementation

The City Action Plan links each recommendation to the problem it is intended to address and the services the city already provides. Depending on the host, the first action may improve an existing transfer service, replace conventional buses with electric vehicles, encourage use of existing rail capacity, or improve sanctioned pedestrian connections and event wayfinding. Documented traffic controls provide complementary operational context without presenting the platform as an engineered traffic-management plan.

For cities with larger structural needs, the app also presents a selective high-investment, high-impact alternative. For example, Dallas's conceptual electric-fleet and corridor package is estimated at approximately $208-$436 million, with potential capacity for 2,925-3,825 passengers per match under the modeled service window. The calculation separates fleet purchases, charging and depot allowances, contingency, and corridor investment. Reserve vehicles, loading assumptions, and slower event cycles constrain the passenger range.

These alternatives are long-term concepts, not funded projects or engineering designs. Capacity is not a forecast of actual ridership. Their purpose is to distinguish an actionable operating improvement from a larger legacy investment and make that tradeoff visible.

Implementation should begin with a city-agency review of the recommended action, followed by a limited pilot. Operators would confirm route length, timetable, fleet availability, charging capability, staffing, accessibility, and actual costs. Passenger counts, replaced service, vehicle miles, energy consumption, and traveler mode surveys would then test whether the intervention delivers the expected benefit. Larger investments would require feasibility analysis and evidence of useful demand beyond event days.

## Limitations and Legacy Value

The prototype is a transparent decision-support tool, not a calibrated crowd simulation or a prediction of realized emissions savings. Beneficiary shares, mode shifts, loading, and several cost allowances remain analyst assumptions. Existing-rail mode-shift cases assume spare capacity. Emissions estimates exclude vehicle manufacturing, construction, and upstream fuel supply chains. Software tests check accounting consistency and application behavior; they do not establish real-world forecasting accuracy.

The platform's lasting value is a repeatable process: establish a baseline, identify the local constraint, define an intervention, quantify its tradeoffs, and validate it in operation. The same approach can support stadium events, conventions, exhibitions, and other concentrated travel demand. By separating immediate operating actions from longer-term infrastructure, it helps cities pursue sustainable event access while directing investment toward benefits that can continue after the event.

## Supplementary Information

### Scoring Conventions

The calculations below describe the scores presented in Portfolio and City Overview. Scores use a 0-100 scale. Define `clip(x) = min(100, max(0, x))`; `ln` denotes the natural logarithm. Maximums and percentiles used for normalization refer to the available host-city data in the current snapshot, not national performance standards. Consequently, refreshing a reference dataset can change relative scores even when a city's own inputs do not change.

Missing data are not automatically assigned zero. Where a composite permits missing inputs, its available weights are rescaled to sum to one: `score = sum(weight * available score) / sum(available weights)`. Additional eligibility rules and exceptions are specified below. Most derived scores are rounded to one decimal place; the transit-stop-density score is rounded to an integer. Calculations can therefore differ slightly from arithmetic using chart labels rounded to whole numbers.

### 1. Overall Mobility Readiness Score

Let `A` be first/last-mile access, `M` traffic management, `H` heat safety, and `V` venue support. With complete eligible evidence, the balanced profile is:

```text
Readiness = 0.30*A + 0.30*M + 0.25*H + 0.15*V
```

The alternative profiles use the following weights, in the same order as the Portfolio heatmap:

| Profile | First/last-mile access | Traffic management | Heat safety | Venue support |
| --- | ---: | ---: | ---: | ---: |
| Balanced | 30% | 30% | 25% | 15% |
| Transit access | 45% | 20% | 10% | 25% |
| Heat resilience | 20% | 15% | 55% | 10% |
| Sustainability | 25% | 20% | 30% | 25% |
| Rice supplied data | 0% | 0% | 55% | 45% |

Custom nonnegative weights are normalized to sum to one. The strict ranking requires eligible observed or derived evidence for every positively weighted component. A partial composite may be calculated from available eligible components with rescaled weights, but is not equivalent to a fully qualified rank. These are policy-weighted indices, not probabilities of successful operations. The Sustainability profile above is a readiness-weighting option, distinct from the separate sustainability score below.

### 2. First/Last-Mile Access Score

Let `D` be transit-stop density, `F` event-window frequency, `E` dedicated-service evidence, `P` pedestrian infrastructure, and `K` parking-facility density, all expressed as normalized scores.

```text
Transit access T = 0.30*D + 0.20*F + 0.35*E + 0.15*P
First/last-mile access A = 0.75*T + 0.25*K
First/last-mile gap score = 100 - A
```

An eligible transit-stop-density input is required. Missing frequency, dedicated-service, or pedestrian inputs are omitted and the remaining transit-access weights are rescaled. If parking evidence is unavailable, `A = T`. A higher access score means stronger modeled venue-side access; a higher gap score means a larger weakness. The gap score is an index, not the separate modeled passenger shortfall in passengers per hour.

Parking increases this access index because nearby vehicle storage is treated as an access resource. It has the opposite effect on sustainability. For example, if `T = 80` and `K = 40`, then `A = 70` and the gap score is `30`. This is an illustrative calculation, not a city result.

### 3. Sustainability Score

Let `L` be fleet electrification, with `K` and `P` as defined above:

```text
Low-parking score = 100 - K
Sustainability = 0.50*(100 - K) + 0.30*L + 0.20*P
```

Missing components are omitted and the remaining weights rescaled; no available components means no score. If `K = 40`, `L = 100`, and `P = 80`, the illustrative sustainability score is `76`. This index represents lower car dependence and stronger electric/active-mobility evidence, not measured CO2e reductions. Summer temperature is used to color the scatterplot but affects neither this score nor the access score.

### 4. Access and Sustainability Component Calculations

**Transit-stop density (`D`).** Let `N_r` be the number of GTFS stops within radius `r` miles of the venue, and `R` the nearby route count:

```text
Raw transit score = 20*N_0.25 + 10*N_0.5 + 5*N_1 + 2*N_2 + 2*min(R, 20)
D = round(100 * raw transit score / maximum available raw transit score)
```

The stop counts are cumulative radii, not mutually exclusive rings: closer stops contribute to multiple terms. This provides extra proximity weighting. The measure includes a capped route-count contribution despite its short display label. Unavailable feeds receive no score; if available feeds all have zero raw scores, their scores are zero. Partial feed evidence remains partial and is not automatically eligible for the access composite.

**Event-window frequency (`F`).** Let `d` be the city's scheduled event-window departure count in the GTFS snapshot and `d_max` the maximum among hosts with observed feed status:

```text
F = 100 * ln(1 + d) / ln(1 + d_max)
```

The logarithm reduces the dominance of very large departure counts. A missing count or non-observed feed yields no score. If all eligible departure counts are zero, the scores are zero. This is a schedule-based supply indicator, not observed passenger throughput.

**Dedicated-service evidence (`E`).** The app reads an analyst-coded tier from cited service evidence:

| Evidence category | Score |
| --- | ---: |
| Documented high-frequency dedicated rail/BRT connection | 100 |
| Dedicated event shuttle/bus service without similarly strong frequency evidence | 60 |
| No coded evidence available | Unavailable |

These tiers are categorical assessments, not measured capacity percentages.

**Pedestrian infrastructure (`P`).** Let `r` be the mapped walking-route distance divided by straight-line distance, `c` the crossing-tag coverage percentage, and `c_max` the largest available host crossing-tag coverage:

```text
Directness score = clip(100 / r)
Crossing evidence score = 100 * c / c_max
P = mean(available directness and crossing evidence scores)
```

Directness requires a positive detour ratio. Crossing evidence is included only when coverage is recorded and `c_max > 0`. If only one component is available, it supplies the score; if neither is available, the score is unavailable. Sidewalk tagging is excluded because it provides no differentiating signal in this snapshot. These inputs describe mapped route and tagging evidence, not an accessibility or pedestrian-safety certification.

**Parking-facility density (`K`).** Let `n` be the number of mapped parking facilities within 0.5 miles of the venue, and `n_max` the largest such count among hosts with eligible derived parking snapshots:

```text
K = 100 * n / n_max
```

Facilities are counted, not parking spaces. A recorded zero receives zero when `n_max > 0`; a missing snapshot remains unavailable. If there is no positive normalization maximum, the current implementation leaves the parking score unavailable. The larger radii shown in the evidence chart provide context but do not enter this score.

**Fleet electrification (`L`).** Cited fleet evidence is assigned a categorical tier:

| Evidence category | Score |
| --- | ---: |
| Substantially electric venue-serving rail/bus fleet | 100 |
| Mixed fleet with meaningful but early bus/BRT electrification | 60 |
| Predominantly diesel/CNG service with limited electric deployment | 30 |
| No coded evidence available | Unavailable |

These are analyst-coded evidence tiers, not the measured percentage of electric vehicles or a fleet emissions inventory.

### 5. Traffic Management Score

The traffic score is **not calculated by a numerical traffic-flow formula**. It is a fixed analyst assessment of cited event controls, coordination, restrictions, and reported operating problems. The current values used by the app are:

| City | Traffic management score |
| --- | ---: |
| Atlanta | 85 |
| Boston | 45 |
| Dallas | 80 |
| Houston | 55 |
| Kansas City | 25 |
| Los Angeles | 35 |
| Miami | 65 |
| New York/New Jersey | 30 |
| Philadelphia | 55 |
| San Francisco Bay Area | 65 |
| Seattle | 80 |

The app retains a city-specific rationale for each value. There is no fitted or independently validated numerical rubric that derives these exact assignments. They should therefore be interpreted as transparent analyst judgments within the composite, not measured congestion reductions or operational success rates.

### 6. Heat Safety Score

Heat safety combines an air-temperature/humidity indicator with a surface urban-heat-island indicator:

```text
Air heat safety = clip(100 - 2.2*max(0, HI_90 - 20))
Surface heat safety = clip(100 - 7*U)
H = 0.50*air heat safety + 0.50*surface heat safety
```

`HI_90` is the 90th percentile of calculated heat-index values in degrees Celsius, using June-July records where available; if no June-July records exist, the implementation uses the available weather records. `U` is the venue p90 surface-UHI value in degrees Celsius, falling back to the dataset's city p90 value when necessary. If one heat component is unavailable, the other receives full weight; if both are unavailable, there is no heat score. The slopes of 2.2 and 7 are index-design choices, not clinical risk thresholds.

For reproducibility, the implemented air heat-index calculation converts air temperature to Fahrenheit (`T`) and uses relative humidity (`RH`, clipped to 0-100). Below 80 degrees Fahrenheit or below 40% humidity, it uses air temperature directly. Otherwise it applies the Rothfusz polynomial:

```text
HI_F = -42.379 + 2.04901523*T + 10.14333127*RH
       - 0.22475541*T*RH - 0.00683783*T^2 - 0.05481717*RH^2
       + 0.00122874*T^2*RH + 0.00085282*T*RH^2
       - 0.00000199*T^2*RH^2
```

For `RH > 85` and `80 <= T <= 87`, the implementation adds `((RH - 85)/10) * ((87 - T)/5)`. The result is converted back to Celsius using `(HI_F - 32)*5/9` before the percentile calculation. The implementation's low-humidity fallback means no separate low-humidity adjustment is applied. Surface UHI is a temperature anomaly, not air temperature or measured human heat exposure.

### 7. Venue Support Score

Let `Q` be the sum of supplied point-of-interest counts within one mile of a city's venue, and `Q_95` the 95th percentile of the available city totals:

```text
V = min(100, 100 * Q / Q_95)
```

The 95th-percentile reference limits the influence of the largest count. The calculation requires a represented city and a positive reference value; otherwise the score is unavailable. It measures surrounding POI concentration as a venue-support proxy, not verified service capacity, opening hours, quality, or accessible routes.

### 8. Worked Readiness Example

Using Dallas's current component values (`A = 50.0`, `M = 80.0`, `H = 47.9`, `V = 0.0`):

```text
Balanced readiness = 0.30*50.0 + 0.30*80.0 + 0.25*47.9 + 0.15*0.0
                   = 50.975
                   = 51.0/100 after rounding
```

A displayed low or zero component describes the recorded data and normalization used by this model; it does not by itself establish that the city has no relevant services. Readiness, access, and sustainability scores should be read alongside their underlying evidence rather than substituted for engineering assessment or measured intervention outcomes.

*Numerical examples reflect the current application model and balanced profile at preparation. They are scenario outputs, not measured tournament outcomes.*
