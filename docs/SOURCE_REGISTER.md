# Supplemental source register

Rice remains the canonical supplied collection. The sources below are
supplemental and become eligible only after an offline pipeline records their
retrieval time, version, license, coverage, and SHA-256 hash in a
`SourceReference`. A URL in this table is not proof that an artifact was pinned.

| Source family | Authoritative reference | Intended use | Required release evidence | Current status |
| --- | --- | --- | --- | --- |
| FIFA | [Official match schedule](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums) | Match ID, venue, date, local kickoff, and stage | Pinned snapshot, timezone validation, venue mapping, retrieval time, version, hash | Integrated: 78 US match events, observed |
| GTFS | [GTFS Schedule reference](https://gtfs.org/documentation/schedule/reference/) plus each pinned agency feed | Stops, routes, calendars, departures, shapes, transfers, pathways, and service span | Agency inventory, feed/archive URL, event-date validity, required files, coverage, retrieval time, hash, license/status | Refreshed 2026-08-02: 78 event-valid match records across 15 feeds and 11 observed cities; 29 records have zero scheduled half-mile capacity |
| OpenStreetMap | [OpenStreetMap copyright and license](https://www.openstreetmap.org/copyright) and pinned venue extracts | Five-mile walking network, route geometry, network distance, isochrones, and tag coverage | Extract boundary/date, ODbL attribution, hash, network QA, tag completeness; no inferred ADA status | Integrated for all 11 venues; eight have routes to event-relevant GTFS stops |
| OSMnx | [OSMnx documentation](https://osmnx.readthedocs.io/) | Reproducible graph extraction and network calculations | Pinned package version and extraction configuration | Integrated with OSMnx 2.1.0 and local GraphML hashes |
| EPA | [Greenhouse Gas Equivalencies calculations](https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator-calculations-and-references) | Low/base/high passenger-vehicle CO2e factors | Pinned factor value, units, model year, conversion, retrieval time, hash | Integrated as scenario planning ranges; not a local MOVES inventory |
| FTA NTD | [National Transit Database data](https://www.transit.dot.gov/ntd/ntd-data) | Agency/mode operating-expense planning ranges | Exact table/year, inflation basis, agency/mode mapping, units, retrieval time, hash | Integrated as estimated order-of-magnitude range |
| FTA Capital Cost Database | [Capital Cost Database](https://www.transit.dot.gov/capital-cost-database) | Conceptual transit capital-cost ranges | Exact release, selected comparable projects, analysis-year adjustment, retrieval time, hash | Integrated as estimated order-of-magnitude range |
| FHWA/PBIC | [Pedestrian and bicycle infrastructure cost resource](https://www.pedbikeinfo.org/resources/resources_details.php?id=4876) | Order-of-magnitude active-mobility treatment costs | Treatment mapping, cost year, inflation method, range, retrieval time, hash | Integrated as estimated order-of-magnitude range |
| NOAA Global Hourly | [NOAA NCEI Integrated Surface Database](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database) | Venue-proximate June-July air temperature and dew-point-derived humidity | Station ID/location, venue distance, hourly coverage, retrieval time, raw hash, and formula | Integrated for Miami and New York/New Jersey only; 366 daily rows |
| USGS Landsat surface temperature | [Landsat Collection 2 Surface Temperature](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature) via [Planetary Computer public mirror](https://planetarycomputer.microsoft.com/dataset/group/landsat) | Boston venue-buffer surface-UHI supplement | Scene IDs/times, QA masks, buffer definitions, pixel coverage, versions, hashes, and semantic limits | Integrated from five valid 2022-2024 scenes; not air temperature or human exposure |
| Official post-event operations | Host agencies and public authorities listed below | Observed tournament ridership, service, fleet, egress, funding, and throughput benchmarks | Raw response hash, publication version/date, coverage, metric locator, unit, granularity, permitted use, and explicit non-use | Integrated: 33 metrics across all 11 cities and 13 match records; no city is match-hour calibration-ready |
| Dallas FIFA 2026 transportation plan | [Dallas Transportation & Mobility Plan](https://www.dallasfwc26.com/dallas-2026/transportation-mobility/) | Source-audit evidence for published transfer hubs, operating windows, and controls | Raw response hash, review terms, source locators, retrieval time, coverage, and a no-runtime-override boundary | Retained for provenance; excluded from the normalized cross-city generated plan |
| Official-plan strategy benchmark | Official host and transit sources linked in `world_cup_2026_strategy_benchmarks.json` | Broad reviewed operating family for every U.S. host | Full city coverage, official HTTPS attribution, reviewed service signals, model/label separation, and artifact hash | Integrated as a calibration audit only; it is not a content-pinned exact operating overlay |

Cost references are conceptual planning inputs, not bids or engineering
estimates. EPA factors are planning factors, not a local fleet inventory or a
MOVES analysis. GTFS represents scheduled service, not actual operations,
ridership, crowding, or reliability.

## Published traffic-management overlay

The compact artifact is
`data/snapshots/operations/world_cup_2026_traffic_management.json` (schema
`1.0.0`). Its artifact SHA-256 is
`07adb936dd0d532a43e6d0a1b517b6d854f8654c88b7536b4d01699bbf4e188b`.
The raw Dallas page is retained in ignored `data/raw/operations/` storage and
must contain the review terms `CentrePort`, `Dynamic Charter Buses`, and
`Griffin Street`. The source-audit overlay does not override the generated
candidate hub, actions, windows, or controls for Dallas or any other city.

## Official-plan strategy benchmark

The compact artifact is
`data/snapshots/operations/world_cup_2026_strategy_benchmarks.json` (schema
`1.0.0`). Its artifact SHA-256 is
`720cd129cf2e9b277c7f425ae8db0f0d5748083aa99031a98b385eb0a80e4e6b`.
It contains one broad strategy-family label and an official source link for
each U.S. host. The classifier is prohibited from reading these labels; the
comparison occurs after prediction. Because raw responses are not republished
in this artifact, the labels cannot authorize exact hub, capacity, window, or
traffic-control claims.

## FIFA 2026 operational-outcome registry

The compact artifact is
`data/snapshots/operations/world_cup_2026_operations.json` (schema `1.2.0`).
Its artifact SHA-256 is
`412595aa8402eadee12940a32167238b4182c5aaa0008fee14b9913f2ff866b0`.

Each source record also stores human-review terms that must be present in the pinned raw response. Snapshot generation fails closed if a source page is empty or those terms disappear, which catches blocked pages and material publisher rewrites before transcribed metrics enter the dashboard.
The ignored `data/raw/operations/` directory contains the corresponding raw
HTTP response bytes. Each `SourceReference.sha256` hashes those bytes, not the
URL or a manually written citation. Raw files are deliberately excluded from
Git, while the compact artifact retains URL, publisher, retrieval time,
version, license, coverage, source type, raw filename, and hash.

Metric extraction is manual and source-located. Every metric records its unit,
granularity, sample size when reported, permitted calibration use, and a
nonempty `not_suitable_for` list. These aggregates are displayed as benchmarks;
they do not alter match-hour demand or access calculations.

| Host market | Pinned official source | Extracted evidence | Outcome status |
| --- | --- | --- | --- |
| Atlanta | [MARTA World Cup Situation Report](https://itsmarta.com/marta-world-cup-situation-report.aspx) | Period rail trips and peak daily rail trips | Observed aggregate |
| Boston | [MBTA/Keolis World Cup train-service results](https://www.keolis.com/en/newsroom-en/news/mbta-and-keolis-deliver-unprecedented-boston-stadium-train-service) | Special-train tickets and two-hour post-match rail egress share | Observed aggregate |
| Dallas | [DART enhanced-service conclusion](https://www.dart.org/about/news-and-events/newsreleases/newsrelease-detail/dart-returns-to-normal-service-frequency) | Agencywide enhanced-period ridership change | Observed aggregate |
| Houston | [Host Committee transportation metrics](https://www.fwc26houston.com/post/fifa-world-cup-2026-houston-host-committee-reports-operational-attendance-and-transportation-metri) | Match attendance, MetroRail boardings, and reported shuttle ridership | Observed/partial match and period aggregates |
| Kansas City | [KC Streetcar World Cup recap](https://kcstreetcar.org/world-cup-recap/) | Tournament ridership, peak day, operating hours, service, and maintenance scale | Observed aggregate |
| Los Angeles | [LA Metro World Cup service results](https://www.metro.net/about/metro-delivers-golden-boot-service-for-world-cup-fans-delivering-more-than-210000-rides-celebratory-customer-experience/) | Direct stadium-service rides and federal service funding | Observed aggregate |
| Miami | [Miami-Dade tournament conclusion](https://www.miamidade.gov/global/release.page?Mduid_release=rel1784578276391561) | Metrorail riders, shuttle boardings, and Fan Festival Metromover trips | Observed aggregate |
| New York/NJ | [NJ interagency transportation after-action report](https://www.njtransit.com/press-releases/new-jersey-interagency-transportation-after-action-report-aar-njny-stadium-fifa) | Tournament totals plus eight match records for NJT, Uber, shuttles, parking, egress, and pedestrian estimates | Observed aggregate and match records |
| Philadelphia | [SEPTA June 2026 ridership](https://wwww.septa.org/news/ridership-june-2026/) | NRG post-match egress and line/system match-day changes | Observed aggregate |
| San Francisco | [BART/VTA stadium-opener report](https://www.bart.gov/news/articles/2026/news20260615-0) | BART transfer, VTA egress time, light-rail and bus ridership, and added-service scale | Observed/partial match aggregate |
| Seattle | [Sound Transit tournament results](https://www.soundtransit.org/blog/platform/tournament-to-remember) | June Link boardings and match-day fleet deployment | Observed/partial aggregate |

### Operational acquisition sources

The next evidence tier should prioritize:

- [FTA monthly ridership](https://www.transit.dot.gov/ntd/monthly-ridership)
  for agency/mode passenger trips, revenue miles, revenue hours, and maximum
  service vehicles. It is a monthly baseline, not event-hour evidence.
- [GTFS Realtime](https://gtfs.org/documentation/realtime/reference/) for trip
  updates, vehicle positions, cancellations, and service alerts. Feeds must be
  archived prospectively unless the publisher supplies history.
- [FHWA NPMRDS](https://ops.fhwa.dot.gov/publications/fhwahop20028/) for
  licensed five-, fifteen-, or sixty-minute National Highway System speeds and
  travel times through an eligible agency/MPO partner.
- [FHWA TMAS](https://www.fhwa.dot.gov/policyinformation/tables/tmasdata/) for
  state-reported continuous hourly traffic counts.
- [Caltrans PeMS](https://dot.ca.gov/programs/traffic-operations/mpr/pems-source),
  [TxDOT traffic monitoring](https://www.txdot.gov/data-maps/traffic-count-maps.html),
  and equivalent state/local portals for venue-corridor detector evidence.

Agency or venue requests remain necessary for 15-minute APC/AFC counts,
match-specific modes, actual passenger loads, shuttle manifests, parking and
curb throughput, pedestrian counts, traffic-control logs, staffing, fleet, and
actual costs. The operational snapshot lists these open fields for every city.

## Environmental supplement registry

The compact artifact is
`data/snapshots/environment/venue_environment.json` (schema `1.0.0`), with
artifact SHA-256
`9b60e5e6b3f2acda78b10ef08478af485383ba3283f92d8ddc9ad75bc18029de`.
It records a narrow replacement policy rather than merging public evidence into
the Rice collection: NOAA replaces weather only for Miami and New York/New
Jersey, and Landsat replaces UHI only for Boston. The original Rice frames stay
available for audit.

| City | Source | Coverage and method | Evidence boundary |
| --- | --- | --- | --- |
| Miami | NOAA Global Hourly station 72202412882, Miami Opa Locka Airport | 2022-2024 June-July; 4.277 miles from venue; daily rows require at least 18 hourly observations | Station air weather, not venue microclimate |
| New York/NJ | NOAA Global Hourly station 72502594741, Teterboro Airport | 2022-2024 June-July; 3.281 miles from venue; daily rows require at least 18 hourly observations | Station air weather, not venue microclimate |
| Boston | USGS Landsat 8/9 Collection 2 Level-2 Surface Temperature via Planetary Computer | Five cloud-masked scenes; two-mile venue buffer compared with a 3-8 mile reference annulus | Surface anomaly, not air temperature, shade, physiological exposure, safety, or ADA evidence |
