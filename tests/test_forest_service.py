"""
Tests for forest service with mocked InterGeoPT API interactions.
"""
import os
# Set environment variables for required settings before importing the module
os.environ["SUPABASE_URL"] = "http://fake"
os.environ["SUPABASE_ANON_KEY"] = "fake"
os.environ["SUPABASE_SERVICE_KEY"] = "fake"
os.environ["SECRET_KEY"] = "fakesecret"

import pytest
import httpx
from fastapi import HTTPException
from backend.app.config import Settings
from backend.app.services.forest_service import ForestService, OverlapRequest, OverlapResponse

@pytest.fixture
def mock_settings(monkeypatch):
    """Fixture to override InterGeoPT API base URL for testing."""
    class TestSettings(Settings):
        INTERGEOPT_API_BASE: str = "https://intergeopt.test/api"

    # Monkeypatch the settings module to return our test settings
    monkeypatch.setattr("backend.app.services.forest_service.settings", TestSettings())
    return TestSettings()

@pytest.fixture
def mock_transport_success():
    """Mock transport that returns a successful InterGeoPT overlap response."""
    def handler(request: httpx.Request) -> httpx.Response:
        # Return a sample successful response from InterGeoPT overlap endpoint
        sample_data = {
            "overlap_area_km2": 12.5,
            "percentage_covered": 45.2,
            "details": {
                "message": "Overlap calculated successfully",
                "features_processed": 124
            }
        }
        return httpx.Response(200, json=sample_data)
    return httpx.MockTransport(handler)

@pytest.fixture
def mock_transport_error():
    """Mock transport that returns an HTTP error."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="Bad Gateway")
    return httpx.MockTransport(handler)

@pytest.fixture
def mock_transport_not_found():
    """Mock transport that returns a 404 error."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")
    return httpx.MockTransport(handler)

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

@pytest.mark.asyncio
async def test_forest_service_init():
    """Test forest service initialization."""
    service = ForestService()
    assert service.http_client is not None

@pytest.mark.asyncio
async def test_check_overlap_success(mock_settings, mock_transport_success):
    """Successful forest overlap check with mocked InterGeoPT API."""
    mock_client = httpx.AsyncClient(transport=mock_transport_success)
    service = ForestService(http_client=mock_client)

    try:
        request = OverlapRequest(geojson={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]})
        response = await service.check_overlap(request)

        assert response is not None
        assert response.overlap_area_km2 == 12.5
        assert response.percentage_covered == 45.2
        assert response.details["message"] == "Overlap calculated successfully"
    finally:
        await mock_client.aclose()

@pytest.mark.asyncio
async def test_check_overlap_http_error(mock_settings, mock_transport_error):
    """Forest overlap check handles HTTP errors."""
    mock_client = httpx.AsyncClient(transport=mock_transport_error)
    service = ForestService(http_client=mock_client)

    try:
        request = OverlapRequest(geojson={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]})
        try:
            await service.check_overlap(request)
            pytest.fail("Expected HTTPException but none was raised")
        except HTTPException as e:
            assert e.status_code == 502
            assert "Bad Gateway" in e.detail
        except Exception as e:
            pytest.fail(f"Unexpected exception type: {type(e)}: {e}")
    finally:
        await mock_client.aclose()

@pytest.mark.asyncio
async def test_check_overlap_not_found(mock_settings, mock_transport_not_found):
    """Forest overlap check handles 404 errors (treated as 502 Bad Gateway)."""
    mock_client = httpx.AsyncClient(transport=mock_transport_not_found)
    service = ForestService(http_client=mock_client)

    try:
        request = OverlapRequest(geojson={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]})
        try:
            await service.check_overlap(request)
            pytest.fail("Expected HTTPException but none was raised")
        except HTTPException as e:
            # Per service design, all upstream HTTP errors are treated as 502 Bad Gateway
            assert e.status_code == 502
            assert "404" in e.detail
            assert "Not Found" in e.detail
        except Exception as e:
            pytest.fail(f"Unexpected exception type: {type(e)}: {e}")
    finally:
        await mock_client.aclose()

@pytest.mark.asyncio
async def test_check_overlap_missing_api_base(monkeypatch):
    """Forest overlap check handles missing API base URL."""
    # Temporarily override settings to have empty API base
    class TestSettings(Settings):
        INTERGEOPT_API_BASE: str = ""

    monkeypatch.setattr("backend.app.services.forest_service.settings", TestSettings())

    service = ForestService()
    request = OverlapRequest(geojson={"type": "Point", "coordinates": [0, 0]})

    try:
        await service.check_overlap(request)
        pytest.fail("Expected HTTPException but none was raised")
    except HTTPException as e:
        assert e.status_code == 503
        assert "not configured" in e.detail
    except Exception as e:
        pytest.fail(f"Unexpected exception type: {type(e)}: {e}")

@pytest.mark.asyncio
async def test_forest_service_close():
    """Test that the service can close its HTTP client."""
    service = ForestService()
    assert service._owns_client is True
    # Should not raise
    await service.close()
    # After closing, we could check if client is closed, but httpx.AsyncClient doesn't expose that easily.
    # We'll just ensure no exception is raised.