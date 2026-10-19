"""
Tests for structural service with comprehensive analysis tests.
"""
import os
# Set environment variables for required settings before importing the module
os.environ["SUPABASE_URL"] = "http://fake"
os.environ["SUPABASE_ANON_KEY"] = "fake"
os.environ["SUPABASE_SERVICE_KEY"] = "fake"
os.environ["SECRET_KEY"] = "fakesecret"

import pytest
from unittest.mock import patch
from backend.app.services.structural_service import StructuralService, BeamRequest, BeamResponse

def test_structural_service_import():
    """Test that the structural service can be imported."""
    assert StructuralService is not None
    assert BeamRequest is not None
    assert BeamResponse is not None

def test_beam_models():
    """Test that BeamRequest and BeamResponse models work."""
    req = BeamRequest(
        length=5.0,
        width=0.3,
        height=0.5,
        youngs_modulus=200e9,
        density=7850,
        yield_stress=250e6,
        point_loads=[{"position": 2.5, "magnitude": 10000.0}],
        supports=[{"position": 0.0, "type": "pin"}, {"position": 5.0, "type": "roller"}]
    )
    assert req.length == 5.0
    assert req.width == 0.3
    assert req.height == 0.5
    assert req.youngs_modulus == 200e9
    assert req.density == 7850
    assert req.yield_stress == 250e6
    assert len(req.point_loads) == 1
    assert req.point_loads[0]["position"] == 2.5
    assert req.point_loads[0]["magnitude"] == 10000.0
    assert len(req.supports) == 2
    assert req.supports[0]["position"] == 0.0
    assert req.supports[0]["type"] =="pin"
    assert req.supports[1]["position"] == 5.0
    assert req.supports[1]["type"] == "roller"

    resp = BeamResponse(
        max_deflection=0.005,
        max_stress=150e6,
        utilization_ratio=0.6,
        details={"analysis": "test"}
    )
    assert resp.max_deflection == 0.005
    assert resp.max_stress == 150e6
    assert resp.utilization_ratio == 0.6
    assert resp.details["analysis"] == "test"

@pytest.mark.asyncio
async def test_analytical_fallback_beam_analysis():
    """Test beam analysis using analytical formulas (when PyNite unavailable)."""
    # We'll temporarily set PYNITE_AVAILABLE to False in the module
    import backend.app.services.structural_service as ss
    original_pynite_available = ss.PYNITE_AVAILABLE
    ss.PYNITE_AVAILABLE = False

    try:
        service = StructuralService()
        # Simple beam: length 5m, width 0.3m, height 0.5m, E=200 GPa, density 7850 kg/m3, yield 250 MPa
        # Point load 10 kN at midspan (2.5m from left)
        request = BeamRequest(
            length=5.0,
            width=0.3,
            height=0.5,
            youngs_modulus=200e9,
            density=7850,
            yield_stress=250e6,
            point_loads=[{"position": 2.5, "magnitude": 10000.0}],
            supports=[{"position": 0.0, "type": "pin"}, {"position": 5.0, "type": "roller"}]
        )

        response = await service.analyze_beam(request)

        # Expected values for simply supported beam with point load at midspan:
        # Max deflection = (P * L^3) / (48 * E * I)
        # I = b * h^3 / 12 = 0.3 * 0.5^3 / 12 = 0.3 * 0.125 / 12 = 0.0375 / 12 = 0.003125 m^4
        # Deflection = (10000 * 5^3) / (48 * 200e9 * 0.003125) = (10000 * 125) / (48 * 200e9 * 0.003125)
        # = 1,250,000 / (48 * 200e9 * 0.003125) = 1,250,000 / (30e6) = 0.0416667 m
        # Max moment = P * L / 4 = 10000 * 5 / 4 = 12500 Nm
        # Max stress = (M * c) / I, c = h/2 = 0.25 m
        # Stress = (12500 * 0.25) / 0.003125 = 3125 / 0.003125 = 1,000,000 Pa = 1.0 MPa
        # Utilization ratio = stress / yield = 1.0e6 / 250e6 = 0.004

        L = request.length
        b = request.width
        h = request.height
        E = request.youngs_modulus
        I = b * h**3 / 12
        P = request.point_loads[0]["magnitude"]
        expected_deflection = (P * L**3) / (48 * E * I)
        expected_moment = P * L / 4
        expected_stress = (expected_moment * (h/2)) / I
        expected_utilization = expected_stress / request.yield_stress

        assert abs(response.max_deflection - expected_deflection) < 1e-6
        assert abs(response.max_stress - expected_stress) < 1e-6
        assert abs(response.utilization_ratio - expected_utilization) < 1e-6
        assert response.details["analysis_method"] == "Analytical (simply supported beam with point load at midspan)"
    finally:
        ss.PYNITE_AVAILABLE = original_pynite_available

@pytest.mark.asyncio
async def test_beam_analysis_with_zero_load():
    """Test beam analysis with zero load returns zero deflection and stress."""
    import backend.app.services.structural_service as ss
    original_pynite_available = ss.PYNITE_AVAILABLE
    ss.PYNITE_AVAILABLE = False

    try:
        service = StructuralService()
        request = BeamRequest(
            length=5.0,
            width=0.3,
            height=0.5,
            youngs_modulus=200e9,
            density=7850,
            yield_stress=250e6,
            point_loads=[],  # No loads
            supports=[{"position": 0.0, "type": "pin"}, {"position": 5.0, "type": "roller"}]
        )

        response = await service.analyze_beam(request)

        assert response.max_deflection == 0.0
        assert response.max_stress == 0.0
        assert response.utilization_ratio == 0.0
        assert response.details["analysis_method"] == "Analytical (simply supported beam with point load at midspan)"
    finally:
        ss.PYNITE_AVAILABLE = original_pynite_available

@pytest.mark.asyncio
async def test_beam_analysis_missing_yield_stress():
    """Test beam analysis handles missing yield stress (should raise HTTPException via validation)."""
    # This is caught by Pydantic validation because yield_stress is required.
    # We'll test that creating a BeamRequest without yield_stress raises validation error.
    with pytest.raises(Exception):
        BeamRequest(
            length=5.0,
            width=0.3,
            height=0.5,
            youngs_modulus=200e9,
            density=7850,
            # yield_stress missing
            point_loads=[{"position": 2.5, "magnitude": 10000.0}],
            supports=[{"position": 0.0, "type": "pin"}, {"position": 5.0, "type": "roller"}]
        )

@pytest.mark.asyncio
async def test_structural_service_init():
    """Test structural service initialization."""
    service = StructuralService()
    assert service is not None

@pytest.mark.asyncio
async def test_structural_service_close():
    """Test that the service can be closed (does nothing)."""
    service = StructuralService()
    # Should not raise
    await service.close()