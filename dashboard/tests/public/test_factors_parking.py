import pytest

from dashboard.pipeline.public.parking import (
    _band_capacity,
    _band_counts,
    _haversine_miles,
    _parse_capacity,
    validate_parking_city,
)


def test_haversine_miles_is_zero_for_the_same_point_and_positive_otherwise():
    assert _haversine_miles(33.7554, -84.4009, 33.7554, -84.4009) == 0.0
    # One degree of latitude is close to 69 miles everywhere on Earth.
    assert 68.0 < _haversine_miles(0.0, 0.0, 1.0, 0.0) < 70.0


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("450", 450),
        ("~500", 500),
        ("120 spaces", 120),
        (None, None),
        ("no", None),
        ("", None),
        ("0", None),
    ],
)
def test_parse_capacity_handles_real_osm_tag_formats(raw, expected):
    assert _parse_capacity(raw) == expected


def test_band_counts_and_capacity_are_cumulative_within_each_ring():
    rows = [
        {"distance_mi": 0.2, "capacity": 100},
        {"distance_mi": 0.7, "capacity": None},
        {"distance_mi": 1.5, "capacity": 50},
        {"distance_mi": 3.0, "capacity": 999},  # beyond the 2 mi search radius in practice
    ]
    counts = _band_counts(rows)
    assert counts == {"facility_count_0_5mi": 1, "facility_count_1mi": 2, "facility_count_2mi": 3}
    capacity = _band_capacity(rows)
    assert capacity == {"tagged_capacity_0_5mi": 100, "tagged_capacity_1mi": 100, "tagged_capacity_2mi": 150}


def test_validate_parking_city_accepts_a_well_formed_derived_row():
    validate_parking_city(
        {
            "city": "Atlanta",
            "status": "derived",
            "facility_count_0_5mi": 2,
            "facility_count_1mi": 5,
            "facility_count_2mi": 9,
            "facilities_with_capacity_tag": 3,
            "total_facilities": 9,
        }
    )


def test_validate_parking_city_accepts_an_unavailable_row_with_no_counts():
    validate_parking_city({"city": "Atlanta", "status": "unavailable", "facility_count_0_5mi": None})


def test_validate_parking_city_rejects_non_monotonic_counts():
    with pytest.raises(ValueError, match="invariant"):
        validate_parking_city(
            {
                "city": "Atlanta",
                "status": "derived",
                "facility_count_0_5mi": 5,
                "facility_count_1mi": 3,
                "facility_count_2mi": 9,
            }
        )


def test_validate_parking_city_rejects_tagged_capacity_exceeding_total_facilities():
    with pytest.raises(ValueError, match="exceeds total"):
        validate_parking_city(
            {
                "city": "Atlanta",
                "status": "derived",
                "facility_count_0_5mi": 1,
                "facility_count_1mi": 2,
                "facility_count_2mi": 3,
                "facilities_with_capacity_tag": 5,
                "total_facilities": 3,
            }
        )
