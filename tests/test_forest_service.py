"""
Tests for forest service.
"""
import pytest
from backend.app.services.forest_service import ForestService, OverlapRequest, OverlapResponse

def test_forest_service_import():
    """Test that the forest service can be imported."""
    assert ForestService is not None
    assert OverlapRequest is not None
    assert OverlapResponse is not None

def test_overlap_models():
    """Test that OverlapRequest and OverlapResponse models work."""
    req = OverlapRequest(geojson={"type": "Point", "coordinates": [0, 0]})
    assert req.geojson["type"] == "Point"
    resp = OverlapResponse(overlap_area_km2=1.5, percentage_covered=25.0, details={"test": "ok"})
    assert resp.overlap_area_km2 == 1.5
    assert resp.percentage_covered == 25.0
    assert resp.details["test"] == "ok"