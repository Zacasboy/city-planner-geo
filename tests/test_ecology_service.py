"""
Tests for ecology service.
"""
import pytest
from backend.app.services.ecology_service import EcologyService, SpeciesRequest, SpeciesResponse

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