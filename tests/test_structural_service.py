"""
Tests for structural service.
"""
import os
# Set environment variables for required settings before importing the module
os.environ["SUPABASE_URL"] = "http://fake"
os.environ["SUPABASE_ANON_KEY"] = "fake"
os.environ["SUPABASE_SERVICE_KEY"] = "fake"
os.environ["SECRET_KEY"] = "fakesecret"

import pytest
from backend.app.services.structural_service import StructuralService, BeamRequest, BeamResponse

def test_structural_service_import():
    """Test that the structural service can be imported."""
    assert StructuralService is not None
    assert BeamRequest is not None
    assert BeamResponse is not None

def test_beam_models():
    """Test that BeamRequest and BeamResponse models work."""
    req = BeamRequest(beam_properties={}, loads={}, supports={})
    assert req.beam_properties == {}
    assert req.loads == {}
    assert req.supports == {}
    resp = BeamResponse(max_deflection=0.0, max_stress=0.0, utilization_ratio=0.0, details={"test": "ok"})
    assert resp.max_deflection == 0.0
    assert resp.max_stress == 0.0
    assert resp.utilization_ratio == 0.0
    assert resp.details["test"] == "ok"