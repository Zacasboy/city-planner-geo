"""
Tests for ecology service with mocked GBIF API interactions.
"""

import os

os.environ.setdefault("SUPABASE_URL", "http://fake")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "fake")
os.environ.setdefault("SUPABASE_SECRET_KEY", "fake")
os.environ.setdefault("SECRET_KEY", "fakesecret")

import httpx
import pytest
from fastapi import HTTPException

from backend.app.services import ecology_service as es
from backend.app.services import http_retry
from backend.app.services.ecology_service import (
    ALLOWED_LICENSES,
    AreaSpeciesRequest,
    EcologyService,
    SpeciesRequest,
    SpeciesResponse,
    species_cache,
)


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    species_cache.clear()
    es.area_cache.clear()

    async def no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(http_retry, "_sleep", no_sleep)


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
            "speciesKey": 7,
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
                {"gbifID": 2, "speciesKey": 123, "decimalLatitude": 1.0, "decimalLongitude": 1.0},
            ],
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


def test_allow_list_is_cc0_and_cc_by_only():
    assert ALLOWED_LICENSES == ("CC0_1_0", "CC_BY_4_0")


@pytest.mark.asyncio
async def test_occurrences_send_license_filter_user_agent_and_cap_limit():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["licenses"] = request.url.params.get_list("license")
        seen["limit"] = request.url.params["limit"]
        seen["ua"] = request.headers["user-agent"]
        return httpx.Response(200, json={"count": 0, "results": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await EcologyService(http_client=client).get_species_occurrences(123, limit=9999)
    assert seen["licenses"] == ["CC0_1_0", "CC_BY_4_0"]
    assert seen["limit"] == "300"
    assert seen["ua"].startswith("city-planner-geo/")
    await client.aclose()


SQUARE = {
    "type": "Polygon",
    # clockwise on purpose: the service must send it anti-clockwise
    "coordinates": [[[-9.4, 38.8], [-9.4, 38.81], [-9.39, 38.81], [-9.39, 38.8], [-9.4, 38.8]]],
}


def _area_handler(seen: list):
    def handler(request: httpx.Request) -> httpx.Response:
        path, params = request.url.path, request.url.params
        if path.startswith("/v1/species/"):
            key = path.rsplit("/", 1)[1]
            return httpx.Response(200, json={"canonicalName": f"Species {key}"})
        seen.append(request)
        if params.get_list("license"):
            return httpx.Response(
                200,
                json={
                    "count": 40,
                    "facets": [
                        {
                            "field": "SPECIES_KEY",
                            "counts": [{"name": "11", "count": 25}, {"name": "22", "count": 15}],
                        }
                    ],
                },
            )
        return httpx.Response(200, json={"count": 55})

    return handler


@pytest.mark.asyncio
async def test_area_species_filters_licenses_and_reports_exclusions():
    seen: list = []
    client = httpx.AsyncClient(transport=httpx.MockTransport(_area_handler(seen)))
    result = await EcologyService(http_client=client).get_area_species(
        AreaSpeciesRequest(geojson=SQUARE, limit=2)
    )
    assert result.total_records == 40
    assert result.records_excluded_by_license == 15
    assert [(s.species_key, s.scientific_name, s.records) for s in result.species] == [
        (11, "Species 11", 25),
        (22, "Species 22", 15),
    ]
    filtered = next(r for r in seen if r.url.params.get_list("license"))
    assert filtered.url.params.get_list("license") == ["CC0_1_0", "CC_BY_4_0"]
    assert filtered.url.params["facet"] == "speciesKey" and filtered.url.params["limit"] == "0"
    assert filtered.url.params["hasGeospatialIssue"] == "false"
    wkt = filtered.url.params["geometry"]
    assert wkt.startswith("POLYGON ((-9.4 38.8, -9.39 38.8")  # anti-clockwise
    assert any("esforço" in n for n in result.notes)
    await client.aclose()


@pytest.mark.asyncio
async def test_area_species_cached():
    seen: list = []
    client = httpx.AsyncClient(transport=httpx.MockTransport(_area_handler(seen)))
    service = EcologyService(http_client=client)
    request = AreaSpeciesRequest(geojson=SQUARE, limit=2)
    await service.get_area_species(request)
    count = len(seen)
    await service.get_area_species(request)
    assert len(seen) == count
    await client.aclose()


@pytest.mark.asyncio
async def test_rate_limit_429_is_retried_with_backoff():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, headers={"Retry-After": "1"}, text="slow down")
        return httpx.Response(200, json={"count": 0, "results": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    result = await EcologyService(http_client=client).get_species_occurrences(1)
    assert result["count"] == 0 and calls["n"] == 3
    await client.aclose()


@pytest.mark.asyncio
async def test_area_species_invalid_area_is_422():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))
    )
    with pytest.raises(HTTPException) as exc:
        await EcologyService(http_client=client).get_area_species(
            AreaSpeciesRequest(geojson={"type": "Point", "coordinates": [0, 0]})
        )
    assert exc.value.status_code == 422
    await client.aclose()


@pytest.mark.asyncio
async def test_area_species_upstream_error_is_502():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(500, text="boom"))
    )
    with pytest.raises(HTTPException) as exc:
        await EcologyService(http_client=client).get_area_species(
            AreaSpeciesRequest(geojson=SQUARE)
        )
    assert exc.value.status_code == 502
    await client.aclose()
