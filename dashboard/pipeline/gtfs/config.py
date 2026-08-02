"""Pinned GTFS feed registry and scenario capacity assumptions."""

GTFS_FEEDS = {
    "Atlanta": [("MARTA", "https://www.itsmarta.com/google_transit_feed/google_transit.zip")],
    "Boston": [("MBTA", "https://cdn.mbta.com/MBTA_GTFS.zip")],
    "Dallas": [("DART", "https://www.dart.org/transitdata/latest/google_transit.zip")],
    "Houston": [("METRO Houston", "https://metro.resourcespace.com/pages/download.php?ref=4835&ext=zip")],
    "Kansas City": [("RideKC/KCATA", "https://ridekc.org/assets/uploads/gtfs/google_transit.zip")],
    "Los Angeles": [
        ("LA Metro Rail", "https://gitlab.com/LACMTA/gtfs_rail/raw/master/gtfs_rail.zip"),
        ("LA Metro Bus", "https://gitlab.com/LACMTA/gtfs_bus/-/raw/master/gtfs_bus.zip"),
    ],
    "Miami": [("Miami-Dade Transit", "https://www.miamidade.gov/transit/googletransit/current/google_transit.zip")],
    "New York/NJ": [("NJ Transit Rail", "https://www.njtransit.com/rail_data.zip")],
    "Philadelphia": [
        ("SEPTA Rail", "https://github.com/septadev/GTFS/releases/latest/download/google_rail.zip"),
        ("SEPTA Bus", "https://github.com/septadev/GTFS/releases/latest/download/google_bus.zip"),
    ],
    "San Francisco": [("VTA", "https://gtfs.vta.org/gtfs_vta.zip")],
    "Seattle": [
        ("Sound Transit", "https://gtfs.sound.obaweb.org/prod/40_gtfs.zip"),
        ("King County Metro", "https://metro.kingcounty.gov/GTFS/google_transit.zip"),
    ],
}

# Passengers per scheduled vehicle, deliberately represented as planning ranges.
MODE_CAPACITY_RANGES = {
    0: {"mode": "tram_light_rail", "low": 120, "base": 180, "high": 250},
    1: {"mode": "subway_metro", "low": 600, "base": 900, "high": 1200},
    2: {"mode": "rail", "low": 500, "base": 800, "high": 1200},
    3: {"mode": "bus", "low": 40, "base": 55, "high": 80},
    4: {"mode": "ferry", "low": 150, "base": 300, "high": 600},
    5: {"mode": "cable_tram", "low": 40, "base": 70, "high": 100},
    6: {"mode": "aerial_lift", "low": 20, "base": 40, "high": 80},
    7: {"mode": "funicular", "low": 60, "base": 100, "high": 180},
    11: {"mode": "trolleybus", "low": 40, "base": 55, "high": 80},
    12: {"mode": "monorail", "low": 150, "base": 250, "high": 400},
}
