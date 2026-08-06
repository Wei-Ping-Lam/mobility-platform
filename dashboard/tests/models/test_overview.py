from __future__ import annotations

import pandas as pd
import pytest

from dashboard.domain.overview import build_portfolio_overview, portfolio_summary

METRICS = pd.DataFrame(
    [
        {
            "city": city,
            "venue": f"{city} Stadium",
            "lat": lat,
            "lon": lon,
            "score": score,
            "rankable": True,
            "transit_score": score,
            "transit_status": "observed",
            "heat_score": 70,
            "heat_status": "derived",
            "uhi_score": 65,
            "uhi_status": "derived",
            "access_score": 60,
            "access_status": "derived",
        }
        for city, lat, lon, score in (
            ("Atlanta", 33.75, -84.39, 72),
            ("Miami", 25.76, -80.19, 64),
        )
    ]
)
ACCESS = [
    {
        "city": "Atlanta",
        "match_id": "ATL-01",
        "status": "scenario",
        "capacity_qualified": True,
        "peak_demand_per_hour": 18000,
        "residual_passengers": 10000,
    },
    {
        "city": "Miami",
        "match_id": "MIA-01",
        "status": "scenario",
        "capacity_qualified": True,
        "peak_demand_per_hour": 16000,
        "residual_passengers": 12000,
    },
]
RECOMMENDATIONS = [
    {
        "city": city,
        "match_id": match_id,
        "intervention": "Added transit frequency",
        "status": "scenario",
        "cost_low": 100000,
        "cost_base": 150000,
        "cost_high": 200000,
        "cost_per_passenger": cost_per_passenger,
        "net_co2e_kg": 300,
        "scope": "Add 6 transit departures per hour in the event window",
        "lead_time_band": "3-12 months",
        "evidence_quality": "medium",
        "evidence_qualified": True,
    }
    for city, match_id, cost_per_passenger in (
        ("Atlanta", "ATL-01", 25),
        ("Miami", "MIA-01", 30),
    )
]
OUTCOMES = [
    {
        "city": city,
        "match_id": match_id,
        "package": {"name": package},
        "status": "scenario",
        "gap_resolved_passengers": gap,
        "cost_low": cost * .8,
        "cost_base": cost,
        "cost_high": cost * 1.2,
        "net_co2e_kg_low": co2e * .5,
        "net_co2e_kg_base": co2e,
        "net_co2e_kg_high": co2e * 1.5,
        "venue_vehicle_trips_low": 8000,
        "venue_vehicle_trips_base": 9000,
        "venue_vehicle_trips_high": 10000,
    }
    for city, match_id in (("Atlanta", "ATL-01"), ("Miami", "MIA-01"))
    for package, gap, cost, co2e in (
        ("Baseline", 0, 0, 0),
        ("Operational Package", 3000, 150000, 400),
        ("Capital Package", 7000, 900000, 1000),
    )
]
WEIGHTS = {"transit": .35, "heat": .2, "uhi": .15, "access": .3}


def test_overview_preserves_comparison_values_and_adds_package_outcomes():
    frame = build_portfolio_overview(
        METRICS,
        ACCESS,
        RECOMMENDATIONS,
        OUTCOMES,
        weights=WEIGHTS,
        package_name="Operational Package",
    )
    assert set(frame["city"]) == {"Atlanta", "Miami"}
    assert frame.loc[frame["city"] == "Miami", "capacity_qualified_gap_pph"].iloc[0] == 12000
    assert set(frame["package_gap_resolved"]) == {3000}
    assert set(frame["package_net_co2e_base"]) == {400}
    assert set(frame["package_cost_per_passenger"]) == {50}
    assert set(frame["top_scope"]) == {"Add 6 transit departures per hour in the event window"}
    assert set(frame["baseline_vehicle_trips_low"]) == {8000}
    assert set(frame["baseline_vehicle_trips_base"]) == {9000}
    assert set(frame["baseline_vehicle_trips_high"]) == {10000}
    assert set(frame["qualified_interventions"]) == {"Added transit frequency"}
    assert frame["top_option_qualified"].all()


def test_package_switch_changes_only_package_outcomes():
    operational = build_portfolio_overview(
        METRICS, ACCESS, RECOMMENDATIONS, OUTCOMES, weights=WEIGHTS, package_name="Operational Package"
    )
    capital = build_portfolio_overview(
        METRICS, ACCESS, RECOMMENDATIONS, OUTCOMES, weights=WEIGHTS, package_name="Capital Package"
    )
    assert operational["capacity_qualified_gap_pph"].equals(capital["capacity_qualified_gap_pph"])
    assert (capital["package_gap_resolved"] > operational["package_gap_resolved"]).all()
    assert (capital["package_cost_base"] > operational["package_cost_base"]).all()


def test_overview_summary_reports_coverage_without_summing_scenarios():
    frame = build_portfolio_overview(METRICS, ACCESS, RECOMMENDATIONS, OUTCOMES, weights=WEIGHTS)
    summary = portfolio_summary(frame, 12)
    assert summary.city_count == 2
    assert summary.match_count == 12
    assert summary.strict_rankable_cities == 2
    assert summary.access_ranked_cities == 2
    assert summary.cities_with_qualified_options == 2
    assert summary.largest_access_gap_pph == 12000


def test_unknown_package_fails_closed():
    with pytest.raises(ValueError, match="Unknown overview package"):
        build_portfolio_overview(METRICS, ACCESS, RECOMMENDATIONS, OUTCOMES, weights=WEIGHTS, package_name="Magic")
