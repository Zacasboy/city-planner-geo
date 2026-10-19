"""
Tests for ecology service with mocked GBIF API interactions.
"""
import pytest
import httpx
from fastapi import HTTPException
from backend.app.services.ecology_service import EcologyService, SpeciesRequest, SpeciesResponse, species_cache

@pytest.fixture
def mock_transport_success():
    """Mock transport that returns a successful GBIF species match response."""
    def handler(request: httpx.Request) -> httpx.Response:
        # Return a sample successful response from GBIF species match endpoint
        sample_data = {
            "usageKey": 123456,
            "scientificName": "Homo sapiens",
            "canonicalName": "Homo sapiens",
            "rank": "SPECIES",
            "status": "ACCEPTED",
            "confidence": 0.98,
            "matchType": "EXACT",
            "kingdom": "Animalia",
            "phylum": "Chordata",
            "class_": "Mammalia",
            "order": "Primates",
            "family": "Hominidae",
            "genus": "Homo",
            "species": "sapiens",
            "kingdomKey": 1,
            "phylumKey": 2,
            "classKey": 3,
            "orderKey": 4,
            "familyKey": 5,
            "genusKey": 6,
            "speciesKey": 7
        }
        return httpx.Response(200, json=sample_data)
    return httpx.MockTransport(handler)

@pytest.fixture
def mock_transport_error():
    """Mock transport that returns an HTTP error."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="Bad Gateway")
    return httpx.MockTransport(handler)

@pytest.mark.asyncio
async def test_ecology_service_import():
    """Test that the ecology service can be imported."""
    assert EcologyService is not None
    assert SpeciesRequest is not None
    assert SpeciesResponse is not None

@pytest.mark.asyncio
async def test_lookup_species_model():
    """Test that SpeciesRequest and SpeciesResponse models work."""
    req = SpeciesRequest(scientific_name="Homo sapiens")
    assert req.scientific_name == "Homo sapiens"
    resp = SpeciesResponse(scientific_name="Homo sapiens", usage_key=123)
    assert resp.scientific_name == "Homo sapiens"
    assert resp.usage_key == 123

@pytest.mark.asyncio
async def test_lookup_species_success(mock_transport_success):
    """Test successful species lookup with mocked GBIF API."""
    # Create service with mocked HTTP client
    mock_client = httpx.AsyncClient(transport=mock_transport_success)
    service = EcologyService(http_client=mock_client)

    try:
        request = SpeciesRequest(scientific_name="Homo sapiens")
        response = await service.lookup_species(request)

        assert response is not None
        assert response.usage_key == 123456
        assert response.scientific_name == "Homo sapiens"
        assert response.confidence == 0.98
        assert response.match_type == "EXACT"
    finally:
        await mock_client.aclose()

@pytest.mark.asyncio
async def test_lookup_species_http_error(mock_transport_error):
    """Test species lookup handles HTTP errors."""
    mock_client = httpx.AsyncClient(transport=mock_transport_error)
    service = EcologyService(http_client=mock_client)

    try:
        request = SpeciesRequest(scientific_name="Homo sapiens")
        try:
            await service.lookup_species(request)
            pytest.fail("Expected HTTPException but none was raised")
        except HTTPException as e:
            assert e.status_code == 502
            assert "Bad Gateway" in e.detail
        except Exception as e:
            pytest.fail(f"Unexpected exception type: {type(e)}: {e}")
    finally:
        await mock_client.aclose()

@pytest.mark.asyncio
async def test_lookup_species_caching(mock_transport_success):
    """Test that species lookup uses cache to avoid duplicate HTTP calls."""
    mock_client = httpx.AsyncClient(transport=mock_transport_success)
    service = EcologyService(http_client=mock_client)

    try:
        request = SpeciesRequest(scientific_name="Homo sapiens")

        # Clear cache before test to ensure deterministic state
        species_cache.clear()

        # First call - should hit the mock transport
        response1 = await service.lookup_species(request)
        assert response1 is not None
        # After first call, cache should have one entry
        assert len(species_cache) == 1

        # Second call - should use cache, no HTTP call made
        response2 = await service.lookup_species(request)
        assert response2 is not None
        assert response2.usage_key == response1.usage_key
        # Cache size should still be 1
        assert len(species_cache) == 1
    finally:
        await mock_client.aclose()

@pytest.mark.asyncio
async def test_get_species_occurrences_success():
    """Test getting species occurrences with mocked GBIF API."""
    def handler(request: httpx.Request) -> httpx.Response:
        # Sample occurrence response
        sample_data = {
            "count": 2,
            "results": [
                {"gbifID": 1, "speciesKey": 123, "decimalLatitude": 0.0, "decimalLongitude": 0.0},
                {"gbifID": 2, "speciesKey": 123, "decimalLatitude": 1.0, "decimalLongitude": 1.0}
            ]
        }
        return httpx.Response(200, json=sample_data)

    mock_transport = httpx.MockTransport(handler)
    mock_client = httpx.AsyncClient(transport=mock_transport)
    service = EcologyService(http_client=mock_client)

    try:
        result = await service.get_species_occurrences(species_key=123, limit=2)
        assert result is not None
        assert result["count"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["gbifID"] == 1
    finally:
        await mock_client.aclose()