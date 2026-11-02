"""Fluxo completo de um utilizador pela API (T1.13): análise, relatório PDF e isolamento."""

from collections.abc import Callable, Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import reports_service
from tests.test_reports_api import FakeStorage

E = 200e9
LOAD_N = 10_000.0
LENGTH_M, WIDTH_M, HEIGHT_M = 5.0, 0.3, 0.5
BEAM = {
    "length": LENGTH_M,
    "width": WIDTH_M,
    "height": HEIGHT_M,
    "youngs_modulus": E,
    "density": 7850,
    "yield_stress": 250e6,
    "include_self_weight": False,
    "point_loads": [{"position": LENGTH_M / 2, "magnitude": LOAD_N}],
    "supports": [{"position": 0.0, "type": "pin"}, {"position": LENGTH_M, "type": "roller"}],
}
PDF_MAGIC = b"%PDF"
PROTECTED_ROUTES = [
    ("post", "/structural/beam"),
    ("post", "/geo/validate"),
    ("post", "/ecology/area-species"),
    ("post", "/morphology/analyze"),
    ("post", "/reports/structural"),
    ("get", "/orchestration/analysis/task-1"),
]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeStorage]:
    fake = FakeStorage()
    monkeypatch.setattr(reports_service, "supabase", MagicMock(storage=fake))
    yield fake


def test_health_is_public(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "healthy"


@pytest.mark.parametrize(("method", "path"), PROTECTED_ROUTES)
def test_protected_routes_reject_anonymous_requests(
    client: TestClient, method: str, path: str
) -> None:
    assert getattr(client, method)(path).status_code in (401, 403)


def test_analysis_then_report_then_isolation(
    client: TestClient, storage: FakeStorage, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    ana, rui = auth_headers("ana"), auth_headers("rui")

    analysis = client.post("/structural/beam", json=BEAM, headers=ana)
    assert analysis.status_code == 200
    result = analysis.json()
    assert result["max_deflection"] > LOAD_N * LENGTH_M**3 / (48 * E * WIDTH_M * HEIGHT_M**3 / 12)
    assert result["details"]["analysis_method"].startswith("FEM: Timoshenko")
    assert "does not replace" in result["details"]["note"]

    created = client.post(
        "/reports/structural", json={"beam_data": BEAM, "analysis_results": result}, headers=ana
    )
    assert created.status_code == 201
    report_id = created.json()["report_id"]
    assert list(storage.files) == [f"ana/{report_id}.pdf"]

    pdf = client.get(f"/reports/{report_id}", headers=ana)
    assert pdf.status_code == 200
    assert pdf.content.startswith(PDF_MAGIC)

    assert client.get(f"/reports/{report_id}", headers=rui).status_code == 404
    assert client.delete(f"/reports/{report_id}", headers=rui).status_code == 404
    assert client.delete(f"/reports/{report_id}", headers=ana).status_code == 200
    assert client.get(f"/reports/{report_id}", headers=ana).status_code == 404
