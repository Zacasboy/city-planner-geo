"""
Tests for morphology service with comprehensive analysis tests.
"""

import os
import time

# Set environment variables for required settings before importing the module
os.environ["SUPABASE_URL"] = "http://fake"
os.environ["SUPABASE_PUBLISHABLE_KEY"] = "fake"
os.environ["SUPABASE_SECRET_KEY"] = "fake"
os.environ["SECRET_KEY"] = "fakesecret"


import pytest
from fastapi import HTTPException

from backend.app.services import morphology_service
from backend.app.services.morphology_service import (
    MorphologyRequest,
    MorphologyResponse,
    MorphologyService,
)
from backend.app.services.obm_source import BuildingSourceError


def test_morphology_service_import():
    """Test that the morphology service can be imported."""
    assert MorphologyService is not None
    assert MorphologyRequest is not None
    assert MorphologyResponse is not None


def test_morphology_models():
    """Test that MorphologyRequest and MorphologyResponse models work."""
    # Test MorphologyRequest
    request = MorphologyRequest(
        geojson={
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[-9.14, 38.72], [-9.14, 38.73], [-9.13, 38.73], [-9.13, 38.72], [-9.14, 38.72]]
                ],
            },
        },
        data_source="mock",
        include_detailed_metrics=True,
    )
    assert request.geojson is not None
    assert request.data_source == "mock"
    assert request.include_detailed_metrics

    # Test MorphologyResponse
    response = MorphologyResponse(
        analysis_area_m2=10000.0,
        building_count=5,
        density_metrics={"building_density_per_km2": 500.0},
        height_metrics={"average_height_m": 10.0},
        height_percentiles={
            "height_25th_percentile": 5.0,
            "height_50th_percentile": 10.0,
            "height_75th_percentile": 15.0,
            "height_90th_percentile": 20.0,
        },
        occupation_metrics={"built_up_percentage": 30.0},
        building_type_metrics={
            "residential_percentage": 60.0,
            "commercial_percentage": 30.0,
            "industrial_percentage": 10.0,
        },
        data_source_used="opendata",
        analysis_method="Test method",
        details={"test": "value"},
    )
    assert response.analysis_area_m2 == 10000.0
    assert response.building_count == 5
    assert response.density_metrics["building_density_per_km2"] == 500.0
    assert response.height_metrics["average_height_m"] == 10.0
    assert response.height_percentiles["height_25th_percentile"] == 5.0
    assert response.height_percentiles["height_50th_percentile"] == 10.0
    assert response.height_percentiles["height_75th_percentile"] == 15.0
    assert response.height_percentiles["height_90th_percentile"] == 20.0
    assert response.occupation_metrics["built_up_percentage"] == 30.0
    assert response.building_type_metrics["residential_percentage"] == 60.0
    assert response.building_type_metrics["commercial_percentage"] == 30.0
    assert response.building_type_metrics["industrial_percentage"] == 10.0
    assert response.data_source_used == "opendata"
    assert response.analysis_method == "Test method"
    assert response.details["test"] == "value"


@pytest.mark.asyncio
async def test_morphology_service_init():
    """Test morphology service initialization."""
    service = MorphologyService()
    assert service is not None


@pytest.mark.asyncio
async def test_morphology_service_close():
    """Test that the service can be closed (does nothing)."""
    service = MorphologyService()
    # Should not raise
    await service.close()


@pytest.mark.asyncio
async def test_morphology_analyze_with_valid_geojson():
    """Test morphology analysis with valid GeoJSON."""
    service = MorphologyService(fetcher=lambda *_: ([], []))

    # Simple square polygon GeoJSON
    request = MorphologyRequest(
        geojson={
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[-9.14, 38.72], [-9.14, 38.73], [-9.13, 38.73], [-9.13, 38.72], [-9.14, 38.72]]
                ],
            },
        },
        data_source="auto",
        include_detailed_metrics=True,
    )

    response = await service.analyze_morphology(request)

    # Check response structure
    assert isinstance(response, MorphologyResponse)
    assert response.analysis_area_m2 > 0
    assert response.building_count >= 0
    assert isinstance(response.density_metrics, dict)
    assert isinstance(response.height_metrics, dict)
    assert isinstance(response.occupation_metrics, dict)
    assert response.data_source_used == "OpenBuildingMap"
    assert isinstance(response.analysis_method, str)
    assert isinstance(response.details, dict)

    # Check that expected metrics are present
    assert "building_density_per_km2" in response.density_metrics
    assert "floor_area_ratio" in response.density_metrics
    assert "ground_space_index" in response.density_metrics

    assert "average_height_m" in response.height_metrics
    assert "max_height_m" in response.height_metrics
    assert "min_height_m" in response.height_metrics

    assert "built_up_percentage" in response.occupation_metrics
    assert "lot_coverage_ratio" in response.occupation_metrics
    assert "ground_space_index" in response.occupation_metrics  # Also in occupation


@pytest.mark.asyncio
async def test_morphology_analyze_with_invalid_geojson():
    """Test morphology analysis with invalid GeoJSON."""
    service = MorphologyService()

    # Invalid GeoJSON (missing required fields)
    request = MorphologyRequest(
        geojson={"type": "FeatureCollection", "features": []},
        data_source="auto",
        include_detailed_metrics=True,
    )

    # This should either return a valid response with zero buildings or raise an HTTPException
    # Depending on implementation, we'll accept either
    try:
        response = await service.analyze_morphology(request)
        # If it doesn't raise an exception, check that we got a valid response
        assert isinstance(response, MorphologyResponse)
    except HTTPException:
        # This is also acceptable
        pass


@pytest.mark.asyncio
async def test_morphology_analyze_different_data_sources():
    """Test morphology analysis with different data source options."""
    service = MorphologyService()

    request = MorphologyRequest(
        geojson={
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[-9.14, 38.72], [-9.14, 38.73], [-9.13, 38.73], [-9.13, 38.72], [-9.14, 38.72]]
                ],
            },
        },
        data_source="mock",
        include_detailed_metrics=False,
    )

    response = await service.analyze_morphology(request)

    assert isinstance(response, MorphologyResponse)
    # When detailed metrics are disabled, we still expect the basic structure
    assert response.analysis_area_m2 > 0
    assert isinstance(response.density_metrics, dict)
    assert isinstance(response.height_metrics, dict)
    assert isinstance(response.occupation_metrics, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


@pytest.fixture(autouse=True)
def _clear_cache():
    morphology_service._cache.clear()
    yield
    morphology_service._cache.clear()


SQUARE = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [[-9.14, 38.72], [-9.14, 38.73], [-9.13, 38.73], [-9.13, 38.72], [-9.14, 38.72]]
        ],
    },
}


def _building(identifier: str, height_m: float | None, kind: str = "residential") -> dict:
    floors = None if height_m is None else round(height_m / 3)
    return {
        "id": identifier,
        "centroid": [-30000.0, -100000.0],
        "footprint_m2": 100.0,
        "area_m2": 100.0 * (floors or 1),
        "height_m": height_m,
        "floors": floors,
        "building_type": kind,
    }


@pytest.mark.asyncio
async def test_real_buildings_report_height_coverage_and_licence():
    buildings = [_building("a", 6.0), _building("b", 12.0), _building("c", None, "other")]
    service = MorphologyService(fetcher=lambda *_: (buildings, ["031332"]))
    response = await service.analyze_morphology(MorphologyRequest(geojson=SQUARE))

    assert response.data_source_used == "OpenBuildingMap"
    assert response.building_count == 3
    assert response.height_metrics["average_height_m"] == 9.0
    assert response.details["buildings_with_height"] == 2
    assert response.details["height_coverage_percent"] == 66.7
    assert response.details["license"] == "ODbL-1.0"
    assert response.details["tiles_missing"] == ["031332"]
    assert any("lower bound" in note for note in response.details["notes"])
    assert response.density_metrics["ground_space_index"] == pytest.approx(
        round(300 / response.analysis_area_m2, 3), abs=1e-3
    )


@pytest.mark.asyncio
async def test_same_area_is_fetched_once():
    calls = []

    def fetcher(*_args):
        calls.append(1)
        return [], []

    service = MorphologyService(fetcher=fetcher)
    request = MorphologyRequest(geojson=SQUARE)
    await service.analyze_morphology(request)
    await service.analyze_morphology(request)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_too_large_area_is_rejected_before_fetching():
    big = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-9.2, 38.7], [-9.2, 38.8], [-9.0, 38.8], [-9.0, 38.7], [-9.2, 38.7]]],
        },
    }
    service = MorphologyService(fetcher=lambda *_: pytest.fail("must not fetch"))
    with pytest.raises(HTTPException) as error:
        await service.analyze_morphology(MorphologyRequest(geojson=big))
    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_unreachable_source_is_503():
    def broken(*_args):
        raise BuildingSourceError("boom")

    area = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[-9.15, 38.72], [-9.15, 38.73], [-9.14, 38.73], [-9.14, 38.72], [-9.15, 38.72]]
            ],
        },
    }
    with pytest.raises(HTTPException) as error:
        await MorphologyService(fetcher=broken).analyze_morphology(MorphologyRequest(geojson=area))
    assert error.value.status_code == 503
    assert "boom" not in error.value.detail


@pytest.mark.asyncio
async def test_slow_source_is_504(monkeypatch):
    monkeypatch.setattr("backend.app.services.morphology_service.FETCH_TIMEOUT_S", 0.05)
    area = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[-9.16, 38.72], [-9.16, 38.73], [-9.15, 38.73], [-9.15, 38.72], [-9.16, 38.72]]
            ],
        },
    }
    with pytest.raises(HTTPException) as error:
        await MorphologyService(fetcher=lambda *_: time.sleep(0.5)).analyze_morphology(
            MorphologyRequest(geojson=area)
        )
    assert error.value.status_code == 504


@pytest.mark.asyncio
async def test_estimated_heights_are_reported_with_licence_and_attribution():
    buildings = [_building("a", 6.0), _building("b", 12.0), _building("c", None)]
    buildings[0]["height_source"] = "obm"
    buildings[1]["height_source"] = "gba_estimate"
    buildings[2]["height_source"] = None
    service = MorphologyService(fetcher=lambda *_: (buildings, ["gba:w010_n40_w005_n35"]))
    response = await service.analyze_morphology(MorphologyRequest(geojson=SQUARE))

    details = response.details
    assert response.data_source_used == "OpenBuildingMap + GlobalBuildingAtlas (estimated heights)"
    assert details["buildings_with_estimated_height"] == 1
    assert details["estimated_height_percent"] == 33.3
    assert "GlobalBuildingAtlas" in details["attribution"]
    assert "OpenBuildingMap" in details["attribution"]
    assert details["license"] == "ODbL-1.0; heights: CC-BY-NC-4.0"
    assert details["tiles_missing"] == []
    assert details["gba_tiles_missing"] == ["gba:w010_n40_w005_n35"]
    assert any("Non-commercial" in note for note in details["notes"])


@pytest.mark.asyncio
async def test_without_estimates_the_gba_licence_is_not_claimed():
    service = MorphologyService(fetcher=lambda *_: ([_building("a", 6.0)], ["gba:unavailable"]))
    response = await service.analyze_morphology(MorphologyRequest(geojson=SQUARE))
    assert response.data_source_used == "OpenBuildingMap"
    assert response.details["license"] == "ODbL-1.0"
    assert "buildings_with_estimated_height" not in response.details
    assert response.details["gba_tiles_missing"] == ["gba:unavailable"]
