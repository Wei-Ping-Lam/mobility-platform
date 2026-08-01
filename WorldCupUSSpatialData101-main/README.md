# Rice University World Cup 2026 U.S. Cities Spatial Data

A curated guide to public spatial and civic data sources for the 11 U.S. host cities of the FIFA World Cup 2026.

This repository features the U.S. host-city network. The goal is to help researchers, journalists, students, planners, civic technologists, and community groups quickly find reputable data for questions about mobility, access, public health, environment, infrastructure, housing, visitors, and regional resilience.

The current U.S. host-city list: Atlanta, Boston, Dallas, Houston, Kansas City, Los Angeles, Miami, New York New Jersey, Philadelphia, San Francisco Bay Area, and Seattle.

## Repository Contents

- [data/sources.csv](data/sources.csv): machine-readable source index.
- [docs/cities/](docs/cities/): one guide for each host city.
- [CONTRIBUTING.md](CONTRIBUTING.md): how to add or correct sources.
- [LICENSE.md](LICENSE.md): license notes for this catalog.

## Host City Scope

FIFA host-city names are regional market names. Several venues sit outside the central city boundary, so each guide includes city, county, regional, state, and transit sources where they matter.

| Host city | Venue geography | City guide |
| --- | --- | --- |
| Atlanta | Mercedes-Benz Stadium, Atlanta, Georgia | [Atlanta](docs/cities/atlanta.md) |
| Boston | Gillette Stadium, Foxborough, Massachusetts | [Boston](docs/cities/boston.md) |
| Dallas | AT&T Stadium, Arlington, Texas | [Dallas](docs/cities/dallas.md) |
| Houston | NRG Stadium, Houston, Texas | [Houston](docs/cities/houston.md) |
| Kansas City | Arrowhead Stadium, Kansas City, Missouri | [Kansas City](docs/cities/kansas-city.md) |
| Los Angeles | SoFi Stadium, Inglewood, California | [Los Angeles](docs/cities/los-angeles.md) |
| Miami | Hard Rock Stadium, Miami Gardens, Florida | [Miami](docs/cities/miami.md) |
| New York/New Jersey | MetLife Stadium, East Rutherford, New Jersey | [New York/New Jersey](docs/cities/new-york-new-jersey.md) |
| Philadelphia | Lincoln Financial Field, Philadelphia, Pennsylvania | [Philadelphia](docs/cities/philadelphia.md) |
| San Francisco Bay Area | Levi's Stadium, Santa Clara, California | [San Francisco Bay Area](docs/cities/san-francisco-bay-area.md) |
| Seattle | Lumen Field, Seattle, Washington | [Seattle](docs/cities/seattle.md) |

## Shared U.S. Geospatial Sources

These national repositories work across all 11 U.S. host cities.

- [ArcGIS Living Atlas of the World](https://livingatlas.arcgis.com/en/home/): authoritative Esri-hosted layers for demographics, environment, hazards, infrastructure, imagery, and boundaries.
- [U.S. Census TIGER/Line Shapefiles](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html): census geographies, roads, water, places, tracts, blocks, and related boundaries.
- [data.census.gov](https://data.census.gov/): demographic, housing, commuting, and economic tables that can be joined to Census geographies.
- [USGS The National Map Downloader](https://apps.nationalmap.gov/downloader/): elevation, hydrography, land cover, structures, and other national base layers.
- [USGS EarthExplorer](https://earthexplorer.usgs.gov/): Landsat and other remotely sensed imagery.
- [FEMA National Flood Hazard Layer](https://www.fema.gov/flood-maps/national-flood-hazard-layer): flood hazard data for screening and planning.
- [EPA Facility Registry Service Geospatial Data](https://www.epa.gov/frs/geospatial-data-download-service): regulated facilities, Superfund, toxic release, and environmental facility identifiers.
- [NOAA Digital Coast](https://coast.noaa.gov/digitalcoast/data/home.html): coastal imagery, shoreline, elevation, land cover, and hazard data for coastal host regions.
- [USDOT Open Data Portal](https://data-usdot.opendata.arcgis.com/): federal transportation datasets and geospatial services.
- [OpenTopography](https://opentopography.org/): LiDAR, DEMs, and terrain data.
- [OpenStreetMap](https://www.openstreetmap.org/) and [Geofabrik U.S. extracts](https://download.geofabrik.de/north-america/us.html): community road, building, sidewalk, amenity, and point-of-interest data.

## City Data Guides

Use these pages when you need local context, high-resolution layers, or the best portals for a specific host market.

- [Atlanta](docs/cities/atlanta.md): City of Atlanta, Fulton County, Atlanta Regional Commission, MARTA, Georgia statewide data.
- [Boston](docs/cities/boston.md): Analyze Boston, Boston GIS, MassGIS, MassDOT, MBTA, MAPC.
- [Dallas](docs/cities/dallas.md): Dallas, Arlington, Dallas County, Tarrant County, NCTCOG, DART, Texas statewide data.
- [Houston](docs/cities/houston.md): City of Houston, Houston Public Works, Harris County, HCAD, H-GAC, Texas statewide data.
- [Kansas City](docs/cities/kansas-city.md): KCMO, Jackson County, MARC, Missouri and Kansas statewide data.
- [Los Angeles](docs/cities/los-angeles.md): LA City, LA County, SCAG, LA Metro, California statewide data.
- [Miami](docs/cities/miami.md): Miami-Dade, Miami Gardens, City of Miami, South Florida regional and Florida statewide data.
- [New York/New Jersey](docs/cities/new-york-new-jersey.md): NYC, New Jersey, Bergen County, NYMTC, NJ TRANSIT, MTA, NY/NJ state data.
- [Philadelphia](docs/cities/philadelphia.md): OpenDataPhilly, CityGeo, DVRPC, SEPTA, PASDA, PennDOT.
- [San Francisco Bay Area](docs/cities/san-francisco-bay-area.md): San Francisco, Santa Clara, San Jose, MTC, VTA, BART, California statewide data.
- [Seattle](docs/cities/seattle.md): Seattle, King County, PSRC, Sound Transit, King County Metro, Washington statewide data.

## Recommended Workflow

1. Start with the city guide for the host market.
2. Check city and county portals first for parcels, streets, boundaries, permits, 311, crashes, public facilities, and public works layers.
3. Use regional planning agencies for travel-demand, land-use, housing, commute, and cross-jurisdiction layers.
4. Use state DOT and geospatial clearinghouses for roads, bridges, imagery, elevation, water, and statewide basemaps.
5. Use the national sources above when you need comparable data across multiple host cities.
6. Record access date, license, coordinate reference system, and any filters used before publishing analysis.

## Responsible Use

This catalog links to public data sources. Public availability does not remove the need for care. Avoid publishing sensitive operational details, personally identifiable information, or data products that could create safety risks for venues, transit operations, workers, residents, or visitors.

## Source Freshness

Government portals move. If a link breaks, open an issue or submit a pull request with a replacement source and the date you checked it.
