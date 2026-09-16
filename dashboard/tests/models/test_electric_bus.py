import pytest

from dashboard.models.electric_bus import electric_bus_kg_per_mile


def test_egrid_units_and_charging_losses_are_explicit():
    assert electric_bus_kg_per_mile("Houston") == pytest.approx(736.629 * 0.45359237 / 1000 * 2.1 / 0.9 / 0.95)


def test_regional_grid_factors_change_emissions():
    assert electric_bus_kg_per_mile("Los Angeles") < electric_bus_kg_per_mile("Boston")
    assert electric_bus_kg_per_mile("Boston") < electric_bus_kg_per_mile("Kansas City")


def test_higher_energy_use_increases_operating_emissions():
    assert electric_bus_kg_per_mile("Miami", "low") < electric_bus_kg_per_mile("Miami") < electric_bus_kg_per_mile("Miami", "high")
