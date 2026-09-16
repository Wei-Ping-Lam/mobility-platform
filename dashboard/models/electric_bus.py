"""Regional operating-emissions scenarios, not measured depot performance."""

from math import isfinite

EGRID_SOURCE = "https://www.epa.gov/egrid/summary-data"
ENERGY_SOURCE = "https://ww2.arb.ca.gov/sites/default/files/barcu/regact/2018/ict2018/appi.pdf"
ENERGY_STRESS_SOURCE = "https://docs.nlr.gov/docs/fy21osti/79444-3.pdf"

# EPA eGRID2023 revision 2, total-output CO2e lb/MWh. Region assignments
# approximate the service area, not an identified charging depot or supplier.
REGIONAL_CO2E_LB_MWH = {
    "CAMX": 429.983, "ERCT": 736.629, "FRCC": 784.785,
    "NEWE": 543.178, "SPNO": 867.740,
}
CITY_GRID_REGION = {
    "Boston": "NEWE", "Dallas": "ERCT", "Houston": "ERCT",
    "Kansas City": "SPNO", "Los Angeles": "CAMX", "Miami": "FRCC",
}
# CARB Appendix I uses 2.1 kWh/mi and 90% charging efficiency. LA100 uses
# 2.84 kWh/mi. The 1.8 lower case and 5% delivery loss are analyst assumptions.
BUS_KWH_PER_MILE = {"low": 1.8, "base": 2.1, "high": 2.84}
CHARGING_EFFICIENCY = 0.90
GRID_DELIVERY_LOSS = 0.05


def electric_bus_kg_per_mile(city: str, energy_case: str = "base") -> float:
    region = CITY_GRID_REGION[city]
    kg_per_generated_kwh = REGIONAL_CO2E_LB_MWH[region] * 0.45359237 / 1000
    return (
        BUS_KWH_PER_MILE[energy_case] / CHARGING_EFFICIENCY
        * kg_per_generated_kwh / (1 - GRID_DELIVERY_LOSS)
    )


def operating_co2e_range(
    city: str, car_miles: float, service_miles: float, replaced_service_miles: float,
    car_factor, conventional_factor,
) -> tuple[float, float]:
    """Factor sensitivity at fixed dispatch and mode shift, not a confidence interval."""
    if not all(isfinite(x) and x >= 0 for x in (car_miles, service_miles, replaced_service_miles)):
        raise ValueError("Mileage must be finite and nonnegative")
    electric_low = electric_bus_kg_per_mile(city, "low") if service_miles else 0
    electric_high = electric_bus_kg_per_mile(city, "high") if service_miles else 0
    return (
        car_miles * car_factor.low + replaced_service_miles * conventional_factor.low - service_miles * electric_high,
        car_miles * car_factor.high + replaced_service_miles * conventional_factor.high - service_miles * electric_low,
    )
