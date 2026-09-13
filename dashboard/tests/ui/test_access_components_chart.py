import pandas as pd

from dashboard.viz.portfolio import access_sustainability_components_chart


def test_access_components_keep_requested_order_and_matching_evidence():
    fields = [
        ("transit_score", "transit_status"),
        ("frequency_score", "frequency_status"),
        ("benchmark_capacity_score", "benchmark_capacity_status"),
        ("pedestrian_infrastructure_score", "pedestrian_infrastructure_status"),
        ("parking_score", "parking_status"),
        ("fleet_electrification_score", "fleet_electrification_status"),
    ]
    row = {"city": "Houston"}
    for index, (score, status) in enumerate(fields, start=1):
        row[score] = index * 10
        row[status] = status

    heatmap = access_sustainability_components_chart(pd.DataFrame([row]), ["Houston"]).data[0]

    assert list(heatmap.x) == [
        "Transit-stop<br>density",
        "Event-window<br>frequency",
        "Dedicated-service<br>evidence",
        "Pedestrian<br>infrastructure",
        "Parking-facility<br>density (0.5mi)",
        "Fleet<br>electrification",
    ]
    assert heatmap.z.tolist() == [[10, 20, 30, 40, 50, 60]]
    assert heatmap.customdata.tolist() == [[status for _, status in fields]]
