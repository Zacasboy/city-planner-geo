"""Testes HTTP da rota /morphology/analyze e do endpoint /structural/beam."""

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app

pytestmark = pytest.mark.filterwarnings("ignore::jwt.warnings.InsecureKeyLengthWarning")

SQUARE_FEATURE = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[0, 0], [0, 100], [100, 100], [100, 0], [0, 0]]],
    },
}


def _auth() -> dict[str, str]:
    token = jwt.encode(
        {"sub": "user-1", "exp": time.time() + 3600}, settings.SECRET_KEY, settings.ALGORITHM
    )
    return {"Authorization": f"Bearer {token}"}


def test_morphology_route_is_registered_once() -> None:
    paths = app.openapi()["paths"]
    assert "/morphology/analyze" in paths
    assert not any(p.startswith("/morphology/morphology") for p in paths)


def test_morphology_requires_authentication() -> None:
    response = TestClient(app).post("/morphology/analyze", json={"geojson": SQUARE_FEATURE})
    assert response.status_code in (401, 403)


def test_morphology_returns_serialisable_metrics_with_samples() -> None:
    response = TestClient(app).post(
        "/morphology/analyze",
        json={"geojson": SQUARE_FEATURE, "include_detailed_metrics": True},
        headers=_auth(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["analysis_area_m2"] == 10_000
    assert body["building_count"] > 0
    assert len(body["details"]["building_samples"]) <= 5


def test_morphology_rejects_invalid_geojson() -> None:
    response = TestClient(app).post(
        "/morphology/analyze", json={"geojson": {"type": "Point"}}, headers=_auth()
    )
    assert response.status_code == 400


def test_structural_beam_endpoint_matches_closed_form() -> None:
    body = {
        "length": 5.0,
        "width": 0.3,
        "height": 0.5,
        "youngs_modulus": 200e9,
        "density": 7850,
        "yield_stress": 250e6,
        "point_loads": [{"position": 2.5, "magnitude": 10000.0}],
        "supports": [{"position": 0.0, "type": "pin"}, {"position": 5.0, "type": "roller"}],
    }
    response = TestClient(app).post("/structural/beam", json=body)
    assert response.status_code == 200
    result = response.json()
    assert result["max_deflection"] == pytest.approx(10000 * 5**3 / (48 * 200e9 * 0.003125))
    assert result["max_stress"] == pytest.approx(1.0e6)
    assert result["utilization_ratio"] == pytest.approx(0.004)
