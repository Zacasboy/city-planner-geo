"""Testes HTTP da rota /morphology/analyze e do endpoint /structural/beam."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from pyproj import Geod
from shapely.geometry import shape

from backend.app.main import app

SQUARE_FEATURE = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [[-9.14, 38.72], [-9.14, 38.73], [-9.13, 38.73], [-9.13, 38.72], [-9.14, 38.72]]
        ],
    },
}


LISBON_BLOCK_AREA_M2 = abs(
    Geod(ellps="GRS80").geometry_area_perimeter(shape(SQUARE_FEATURE["geometry"]))[0]
)


def test_morphology_rejects_area_outside_portugal(
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    luanda = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[13.20, -8.85], [13.20, -8.84], [13.21, -8.84], [13.21, -8.85], [13.20, -8.85]]
            ],
        },
    }
    response = TestClient(app).post(
        "/morphology/analyze", json={"geojson": luanda}, headers=auth_headers("user-1")
    )
    assert response.status_code == 400
    assert "EPSG:3763" in response.json()["error"]["message"]


def test_morphology_route_is_registered_once() -> None:
    paths = app.openapi()["paths"]
    assert "/morphology/analyze" in paths
    assert not any(p.startswith("/morphology/morphology") for p in paths)


def test_morphology_requires_authentication() -> None:
    response = TestClient(app).post("/morphology/analyze", json={"geojson": SQUARE_FEATURE})
    assert response.status_code in (401, 403)


def test_morphology_returns_serialisable_metrics_with_samples(
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    response = TestClient(app).post(
        "/morphology/analyze",
        json={"geojson": SQUARE_FEATURE, "include_detailed_metrics": True},
        headers=auth_headers("user-1"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["analysis_area_m2"] == pytest.approx(LISBON_BLOCK_AREA_M2, rel=1e-3)
    for sample in body["details"]["building_samples"]:
        lng, lat = sample["centroid"]
        assert -9.14 < lng < -9.13
        assert 38.72 < lat < 38.73
    assert body["building_count"] > 0
    assert len(body["details"]["building_samples"]) <= 5


def test_morphology_rejects_invalid_geojson(
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    response = TestClient(app).post(
        "/morphology/analyze", json={"geojson": {"type": "Point"}}, headers=auth_headers("user-1")
    )
    assert response.status_code == 400


def test_structural_beam_endpoint_matches_closed_form(
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    body = {
        "length": 5.0,
        "width": 0.3,
        "height": 0.5,
        "youngs_modulus": 200e9,
        "density": 7850,
        "yield_stress": 250e6,
        "point_loads": [{"position": 2.5, "magnitude": 10000.0}],
        "include_self_weight": False,
        "include_shear_deformation": False,
        "supports": [{"position": 0.0, "type": "pin"}, {"position": 5.0, "type": "roller"}],
    }
    response = TestClient(app).post("/structural/beam", json=body, headers=auth_headers("user-1"))
    assert response.status_code == 200
    result = response.json()
    assert result["max_deflection"] == pytest.approx(10000 * 5**3 / (48 * 200e9 * 0.003125))
    assert result["max_stress"] == pytest.approx(1.0e6)
    assert result["utilization_ratio"] == pytest.approx(0.004)
