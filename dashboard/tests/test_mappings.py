from dashboard.mobility_platform.mappings import cities_for_market


def test_combined_market_mapping_is_explicit():
    assert cities_for_market("Dallas / Houston") == ("Dallas", "Houston")
    assert cities_for_market("Los Angeles / SF Bay Area") == ("Los Angeles", "San Francisco")


def test_unknown_market_is_not_falsely_assigned():
    assert cities_for_market("Unknown / Other") == tuple()
