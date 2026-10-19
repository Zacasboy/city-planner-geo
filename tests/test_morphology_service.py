"""
Tests for morphology service with comprehensive analysis tests.
"""
import os
# Set environment variables for required settings before importing the module
os.environ["SUPABASE_URL"] = "http://fake"
os.environ["SUPABASE_ANON_KEY"] = "fake"
os.environ["SUPABASE_SERVICE_KEY"] = "fake"
os.environ["SECRET_KEY"] = "fakesecret"

import pytest
from unittest.mock import patch
from fastapi import HTTPException
from backend.app.services.morphology_service import MorphologyService, MorphologyRequest, MorphologyResponse

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
                "coordinates": [[
                    [0, 0],
                    [0, 100],
                    [100, 100],
                    [100, 0],
                    [0, 0]
                ]]
            }
        },
        data_source="opendata",
        include_detailed_metrics=True
    )
    assert request.geojson is not None
    assert request.data_source == "opendata"
    assert request.include_detailed_metrics == True

    # Test MorphologyResponse
    response = MorphologyResponse(
        analysis_area_m2=10000.0,
        building_count=5,
        density_metrics={"building_density_per_km2": 500.0},
        height_metrics={"average_height_m": 10.0},
        height_percentiles={"height_25th_percentile": 5.0, "height_50th_percentile": 10.0, "height_75th_percentile": 15.0, "height_90th_percentile": 20.0},
        occupation_metrics={"built_up_percentage": 30.0},
        building_type_metrics={"residential_percentage": 60.0, "commercial_percentage": 30.0, "industrial_percentage": 10.0},
        data_source_used="opendata",
        analysis_method="Test method",
        details={"test": "value"}
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
    service = MorphologyService()

    # Simple square polygon GeoJSON
    request = MorphologyRequest(
        geojson={
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0],
                    [0, 100],
                    [100, 100],
                    [100, 0],
                    [0, 0]
                ]]
            }
        },
        data_source="auto",
        include_detailed_metrics=True
    )

    response = await service.analyze_morphology(request)

    # Check response structure
    assert isinstance(response, MorphologyResponse)
    assert response.analysis_area_m2 > 0
    assert response.building_count >= 0
    assert isinstance(response.density_metrics, dict)
    assert isinstance(response.height_metrics, dict)
    assert isinstance(response.occupation_metrics, dict)
    assert response.data_source_used in ["auto", "opendata", "dbsm", "mock/sample"]
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
        geojson={
            "type": "FeatureCollection",
            "features": []
        },
        data_source="auto",
        include_detailed_metrics=True
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
                "coordinates": [[
                    [0, 0],
                    [0, 50],
                    [50, 50],
                    [50, 0],
                    [0, 0]
                ]]
            }
        },
        data_source="opendata",
        include_detailed_metrics=False
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