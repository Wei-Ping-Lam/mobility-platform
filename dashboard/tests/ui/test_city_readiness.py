import pandas as pd

from dashboard.ui.pages.overview import _readiness_components
from dashboard.viz.portfolio import READINESS_COMPONENTS


def test_city_readiness_keeps_bars_with_portfolio_components():
    figure = _readiness_components({
        "gap_score": 50, "transit_score": 0, "traffic_score": 80,
        "heat_score": 48, "access_score": 100,
    })
    trace = figure.data[0]
    assert trace.type == "bar"
    assert trace.orientation == "h"
    assert list(trace.y) == list(READINESS_COMPONENTS)
    assert list(trace.x) == [50, 80, 48, 100]
    assert figure.layout.yaxis.autorange == "reversed"
    assert list(figure.layout.xaxis.range) == [0, 100]
    assert trace.cliponaxis is False


def test_city_readiness_does_not_turn_missing_scores_into_zero():
    figure = _readiness_components({"gap_score": 50, "gap_status": "derived"})
    trace = figure.data[0]
    assert len(trace.x) == 4
    assert pd.isna(trace.x[1])
    assert trace.customdata[0][0] == "derived"
    assert trace.customdata[1][0] == "unavailable"
