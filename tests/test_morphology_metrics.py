"""Testes das métricas de morfologia, com valores calculados à mão."""

import pytest
from shapely.geometry import Polygon

from backend.app.services import morphology_metrics as metrics
from backend.app.services.morphology_data import (
    extract_polygon,
    generate_mock_buildings,
    is_valid_geojson,
)

AREA_M2 = 10_000.0
BUILDINGS = [
    {
        "area_m2": 100,
        "footprint_m2": 50,
        "height_m": 10,
        "floors": 3,
        "building_type": "residential",
    },
    {
        "area_m2": 100,
        "footprint_m2": 50,
        "height_m": 20,
        "floors": 6,
        "building_type": "residential",
    },
    {
        "area_m2": 100,
        "footprint_m2": 50,
        "height_m": 30,
        "floors": 9,
        "building_type": "commercial",
    },
    {
        "area_m2": 100,
        "footprint_m2": 50,
        "height_m": 40,
        "floors": 12,
        "building_type": "industrial",
    },
]


def test_density_metrics() -> None:
    assert metrics.density_metrics(BUILDINGS, AREA_M2) == {
        "building_density_per_km2": 400.0,
        "floor_area_ratio": 0.04,
        "ground_space_index": 0.02,
    }


def test_height_metrics() -> None:
    assert metrics.height_metrics(BUILDINGS) == {
        "average_height_m": 25.0,
        "max_height_m": 40.0,
        "min_height_m": 10.0,
        "height_std_dev": 11.18,
        "average_floors": 7.5,
    }


def test_height_percentiles_use_linear_interpolation() -> None:
    assert metrics.height_percentiles(BUILDINGS) == {
        "height_25th_percentile": 17.5,
        "height_50th_percentile": 25.0,
        "height_75th_percentile": 32.5,
        "height_90th_percentile": 37.0,
    }


def test_occupation_metrics() -> None:
    assert metrics.occupation_metrics(BUILDINGS, AREA_M2) == {
        "ground_space_index": 0.02,
        "lot_coverage_ratio": 0.02,
        "built_up_percentage": 2.0,
    }


def test_building_type_metrics() -> None:
    assert metrics.building_type_metrics(BUILDINGS) == {
        "residential_percentage": 50.0,
        "commercial_percentage": 25.0,
        "industrial_percentage": 25.0,
    }


def test_untyped_buildings_count_as_residential() -> None:
    result = metrics.building_type_metrics([{"height_m": 3}])
    assert result["residential_percentage"] == 100.0


def test_single_building_has_zero_std_dev_and_flat_percentiles() -> None:
    one = [{"height_m": 12, "floors": 4}]
    assert metrics.height_metrics(one)["height_std_dev"] == 0.0
    assert set(metrics.height_percentiles(one).values()) == {12.0}


@pytest.mark.parametrize(
    "func",
    [
        metrics.height_metrics,
        metrics.height_percentiles,
        metrics.building_type_metrics,
    ],
)
def test_empty_input_gives_zeros(func) -> None:
    assert set(func([]).values()) == {0.0}


@pytest.mark.parametrize("func", [metrics.density_metrics, metrics.occupation_metrics])
def test_zero_area_gives_zeros(func) -> None:
    assert set(func(BUILDINGS, 0).values()) == {0.0}


SQUARE = Polygon([(0, 0), (0, 300), (300, 300), (300, 0)])


def test_mock_buildings_are_deterministic() -> None:
    assert generate_mock_buildings(SQUARE) == generate_mock_buildings(SQUARE)


def test_mock_buildings_lie_inside_the_polygon() -> None:
    buildings = generate_mock_buildings(SQUARE)
    assert len(buildings) == 225
    assert all(SQUARE.contains(__import__("shapely").Point(*b["centroid"])) for b in buildings)


def test_mock_buildings_are_json_serialisable() -> None:
    import json

    json.dumps(generate_mock_buildings(SQUARE))


def test_geojson_helpers() -> None:
    feature = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [0, 5], [5, 5], [0, 0]]]},
    }
    assert is_valid_geojson(feature)
    assert not is_valid_geojson({"type": "Point"})
    assert not is_valid_geojson("texto")
    assert extract_polygon(feature) is not None
    assert extract_polygon({"type": "FeatureCollection", "features": []}) is None
    assert extract_polygon({"type": "Feature", "geometry": None}) is None


def test_polygon_projection_gives_square_metres() -> None:
    from backend.app.services.geo_utils import polygon_wgs84_to_tm06

    block = Polygon([(-9.14, 38.72), (-9.14, 38.73), (-9.13, 38.73), (-9.13, 38.72)])
    projected = polygon_wgs84_to_tm06(block)
    assert 0.9e6 < projected.area < 1.0e6  # ~0,0087° x 0,011° ≈ 0,96 km²


def test_polygon_projection_rejects_degrees_outside_portugal() -> None:
    from backend.app.services.geo_utils import polygon_wgs84_to_tm06

    with pytest.raises(ValueError, match="EPSG:3763"):
        polygon_wgs84_to_tm06(Polygon([(0, 0), (0, 100), (100, 100), (100, 0)]))
