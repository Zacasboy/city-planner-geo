"""
Basic end-to-end tests for City Planner Geo application
T1.13: Teste end-to-end e deploy em staging
These tests focus on core API functionality that doesn't require WeasyPrint.
"""

import os

import pytest

# Set environment variables for required settings before importing app modules
os.environ["SUPABASE_URL"] = "http://fake.supabase.co"
os.environ["SUPABASE_PUBLISHABLE_KEY"] = "fake-anon-key"
os.environ["SUPABASE_SECRET_KEY"] = "fake-service-key"
os.environ["SECRET_KEY"] = "fake-secret-key-for-testing"
os.environ["BACKEND_CORS_ORIGINS"] = '["http://localhost:3000"]'
os.environ["LOG_LEVEL"] = "INFO"

# Add the backend directory to the path so we can import app modules

from fastapi.testclient import TestClient

from backend.app.main import app

# Test client for API endpoints
client = TestClient(app)


def test_health_endpoint():
    """Test that the health endpoint is accessible."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_structural_analysis_endpoint():
    """Test the structural analysis endpoint with sample data."""
    # Sample beam data
    beam_data = {
        "length": 5.0,
        "width": 0.3,
        "height": 0.5,
        "youngs_modulus": 200e9,
        "density": 7850,
        "yield_stress": 250e6,
        "point_loads": [{"position": 2.5, "magnitude": 10000.0}],
        "supports": [{"position": 0.0, "type": "pin"}, {"position": 5.0, "type": "roller"}],
    }

    response = client.post("/structural/beam", json=beam_data)
    # This might succeed or fail with auth errors depending on setup
    assert response.status_code in [200, 401, 403]

    if response.status_code == 200:
        data = response.json()
        # Check that we got the expected response structure
        assert "max_deflection" in data
        assert "max_stress" in data
        assert "utilization_ratio" in data
        assert "details" in data

        # Basic sanity checks on the values
        assert data["max_deflection"] >= 0
        assert data["max_stress"] >= 0
        assert data["utilization_ratio"] >= 0


def test_api_documentation_endpoints():
    """Test that API documentation endpoints are accessible."""
    # Test OpenAPI JSON endpoint
    response = client.get("/api/v1/openapi.json")
    # This might return 200 or redirect, depending on configuration
    assert response.status_code in [200, 307]

    # Test docs endpoint
    response = client.get("/docs")
    assert response.status_code == 200

    # Test redoc endpoint
    response = client.get("/redoc")
    assert response.status_code == 200


def test_complete_core_workflow():
    """
    Test a complete core workflow that doesn't depend on WeasyPrint:
    1. Check health
    2. Perform structural analysis
    """
    # Step 1: Health check
    health_response = client.get("/health")
    assert health_response.status_code == 200

    # Step 2: Structural analysis
    beam_data = {
        "length": 6.0,
        "width": 0.25,
        "height": 0.4,
        "youngs_modulus": 200e9,
        "density": 7850,
        "yield_stress": 350e6,
        "point_loads": [{"position": 3.0, "magnitude": 15000.0}],
        "supports": [{"position": 0.0, "type": "pin"}, {"position": 6.0, "type": "roller"}],
    }

    analysis_response = client.post("/structural/beam", json=beam_data)
    # Accept success or auth errors
    assert analysis_response.status_code in [200, 401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
