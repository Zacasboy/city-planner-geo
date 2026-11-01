"""As rotas de dados exigem autenticação (T1.2)."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

PROTECTED_REQUESTS = [
    ("post", "/geo/validate", {"json": {}}),
    ("post", "/geo/convert", {"json": {}}),
    ("get", "/geo/wgs84-to-tm06/-9.1/38.7", {}),
    ("get", "/geo/tm06-to-wgs84/-86000/-105000", {}),
    ("post", "/ecology/area-species", {"json": {}}),
    ("post", "/ecology/species", {"json": {}}),
    ("get", "/ecology/species/1/occurrences", {}),
    ("get", "/ecology/cache/stats", {}),
    ("post", "/forest/overlap", {"json": {}}),
    ("post", "/structural/beam", {"json": {}}),
]


@pytest.mark.parametrize(("method", "path", "kwargs"), PROTECTED_REQUESTS)
def test_route_rejects_missing_token(method: str, path: str, kwargs: dict) -> None:
    response = getattr(TestClient(app), method)(path, **kwargs)
    assert response.status_code in (401, 403)


@pytest.mark.parametrize(("method", "path", "kwargs"), PROTECTED_REQUESTS)
def test_route_rejects_invalid_token(method: str, path: str, kwargs: dict) -> None:
    headers = {"Authorization": "Bearer not-a-jwt"}
    response = getattr(TestClient(app), method)(path, headers=headers, **kwargs)
    assert response.status_code == 401


def test_valid_token_reaches_the_route(auth_headers: Callable[[str], dict[str, str]]) -> None:
    response = TestClient(app).post("/geo/validate", json={}, headers=auth_headers("user-1"))
    assert response.status_code not in (401, 403)


def test_health_stays_public() -> None:
    assert TestClient(app).get("/health").status_code == 200
