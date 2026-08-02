# Supplemental source register

Rice remains the canonical supplied collection. The sources below are
supplemental and become eligible only after an offline pipeline records their
retrieval time, version, license, coverage, and SHA-256 hash in a
`SourceReference`. A URL in this table is not proof that an artifact was pinned.

| Source family | Authoritative reference | Intended use | Required release evidence | Current status |
| --- | --- | --- | --- | --- |
| FIFA | [Official match schedule](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums) | Match ID, venue, date, local kickoff, and stage | Pinned snapshot, timezone validation, venue mapping, retrieval time, version, hash | Integrated: 78 US match events, observed |
| GTFS | [GTFS Schedule reference](https://gtfs.org/documentation/schedule/reference/) plus each official agency feed | Stops, routes, calendars, departures, shapes, transfers, pathways, and service span | Agency inventory, feed URL, event-date validity, required files, coverage, retrieval time, hash, license/status | Refreshed 2026-08-02: 38 event-valid matches across 4 observed and 2 partial cities; 3 outside-window and 2 failed-feed cities |
| OpenStreetMap | [OpenStreetMap copyright and license](https://www.openstreetmap.org/copyright) and pinned venue extracts | Five-mile walking network, route geometry, network distance, isochrones, and tag coverage | Extract boundary/date, ODbL attribution, hash, network QA, tag completeness; no inferred ADA status | Integrated for all 11 venues; route geometry remains partial where event-relevant GTFS stops are unavailable |
| OSMnx | [OSMnx documentation](https://osmnx.readthedocs.io/) | Reproducible graph extraction and network calculations | Pinned package version and extraction configuration | Integrated with OSMnx 2.1.0 and local GraphML hashes |
| EPA | [Greenhouse Gas Equivalencies calculations](https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator-calculations-and-references) | Low/base/high passenger-vehicle CO2e factors | Pinned factor value, units, model year, conversion, retrieval time, hash | Integrated as scenario planning ranges; not a local MOVES inventory |
| FTA NTD | [National Transit Database data](https://www.transit.dot.gov/ntd/ntd-data) | Agency/mode operating-expense planning ranges | Exact table/year, inflation basis, agency/mode mapping, units, retrieval time, hash | Integrated as estimated order-of-magnitude range |
| FTA Capital Cost Database | [Capital Cost Database](https://www.transit.dot.gov/capital-cost-database) | Conceptual transit capital-cost ranges | Exact release, selected comparable projects, analysis-year adjustment, retrieval time, hash | Integrated as estimated order-of-magnitude range |
| FHWA/PBIC | [Pedestrian and bicycle infrastructure cost resource](https://www.pedbikeinfo.org/resources/resources_details.php?id=4876) | Order-of-magnitude active-mobility treatment costs | Treatment mapping, cost year, inflation method, range, retrieval time, hash | Integrated as estimated order-of-magnitude range |

Cost references are conceptual planning inputs, not bids or engineering
estimates. EPA factors are planning factors, not a local fleet inventory or a
MOVES analysis. GTFS represents scheduled service, not actual operations,
ridership, crowding, or reliability.
