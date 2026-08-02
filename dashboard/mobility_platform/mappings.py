"""Canonical host-city, venue, market, and weather mappings."""

from __future__ import annotations

HOST_CITIES: dict[str, dict[str, object]] = {
    "Atlanta": {"state": "GA", "market": "Atlanta", "venue": "Mercedes-Benz Stadium", "lat": 33.7554, "lon": -84.4009, "capacity": 71000, "games": 8},
    "Boston": {"state": "MA", "market": "Boston", "venue": "Gillette Stadium", "lat": 42.0909, "lon": -71.2643, "capacity": 65878, "games": 7},
    "Dallas": {"state": "TX", "market": "Dallas", "venue": "AT&T Stadium", "lat": 32.7480, "lon": -97.0929, "capacity": 80000, "games": 9},
    "Houston": {"state": "TX", "market": "Houston", "venue": "NRG Stadium", "lat": 29.6851, "lon": -95.4106, "capacity": 72220, "games": 7},
    "Kansas City": {"state": "MO", "market": "Kansas City", "venue": "Arrowhead Stadium", "lat": 39.0489, "lon": -94.4839, "capacity": 76416, "games": 6},
    "Los Angeles": {"state": "CA", "market": "Los Angeles", "venue": "SoFi Stadium", "lat": 33.9534, "lon": -118.3387, "capacity": 70240, "games": 8},
    "Miami": {"state": "FL", "market": "Miami", "venue": "Hard Rock Stadium", "lat": 25.9579, "lon": -80.2388, "capacity": 65326, "games": 7},
    "New York/NJ": {"state": "NJ", "market": "New York/New Jersey", "venue": "MetLife Stadium", "lat": 40.8135, "lon": -74.0745, "capacity": 82500, "games": 8},
    "Philadelphia": {"state": "PA", "market": "Philadelphia", "venue": "Lincoln Financial Field", "lat": 39.9008, "lon": -75.1675, "capacity": 69796, "games": 6},
    "San Francisco": {"state": "CA", "market": "San Francisco Bay Area", "venue": "Levi's Stadium", "lat": 37.4033, "lon": -121.9700, "capacity": 68500, "games": 6},
    "Seattle": {"state": "WA", "market": "Seattle", "venue": "Lumen Field", "lat": 47.5952, "lon": -122.3316, "capacity": 72000, "games": 6},
}

PRIMARY_WEATHER_STATIONS = {
    "Atlanta": "KATL", "Boston": "KBOS", "Dallas": "KDFW", "Houston": "KHOU",
    "Kansas City": "KMCI", "Los Angeles": "KLAX", "Miami": "KMIA",
    "New York/NJ": "KJFK", "Philadelphia": "KPHL", "San Francisco": "KSFO", "Seattle": "KSEA",
}

# The supplied daily-weather-rice collection is missing partition 2_0_0, which
# contains ten primary host-city stations. These are the nearest station IDs
# actually present in the supplied observations. Coordinates and distances were
# resolved against NOAA NCEI's official ISD station-history metadata.
WEATHER_STATION_METADATA = {
    "Atlanta": {"station": "KMGE", "name": "Dobbins Air Reserve Base Airport", "distance_mi": 13.0},
    "Boston": {"station": "KOWD", "name": "Norwood Memorial Airport", "distance_mi": 8.3},
    "Dallas": {"station": "KRBD", "name": "Dallas Executive Airport", "distance_mi": 13.9},
    "Houston": {"station": "KDWH", "name": "Hooks Memorial Airport", "distance_mi": 27.9},
    "Kansas City": {"station": "KIXD", "name": "New Century Aircenter Airport", "distance_mi": 26.9},
    "Los Angeles": {"station": "KTOA", "name": "Zamperini Field Airport", "distance_mi": 10.4},
    "Miami": {"station": "KHST", "name": "Homestead AFB Airport", "distance_mi": 34.0},
    "New York/NJ": {"station": "KISP", "name": "Long Island MacArthur Airport", "distance_mi": 50.9},
    "Philadelphia": {"station": "KPHL", "name": "Philadelphia International Airport", "distance_mi": 3.7},
    "San Francisco": {"station": "KNUQ", "name": "Moffett Federal Airfield", "distance_mi": 4.3},
    "Seattle": {"station": "KPWT", "name": "Bremerton National Airport", "distance_mi": 21.7},
}
WEATHER_STATIONS = {city: str(metadata["station"]) for city, metadata in WEATHER_STATION_METADATA.items()}

# Exact source labels to canonical city names. No substring matching is used.
MARKET_TO_CITY = {
    "Atlanta": "Atlanta",
    "Boston": "Boston",
    "Dallas": "Dallas",
    "Dallas / Houston": None,
    "Houston": "Houston",
    "Kansas City": "Kansas City",
    "Los Angeles": "Los Angeles",
    "Los Angeles / SF Bay Area": None,
    "Miami": "Miami",
    "New York/New Jersey": "New York/NJ",
    "Philadelphia": "Philadelphia",
    "San Francisco Bay Area": "San Francisco",
    "Seattle": "Seattle",
}


def cities_for_market(market: str) -> tuple[str, ...]:
    if market == "Dallas / Houston":
        return ("Dallas", "Houston")
    if market == "Los Angeles / SF Bay Area":
        return ("Los Angeles", "San Francisco")
    city = MARKET_TO_CITY.get(market)
    return (city,) if city else tuple()
