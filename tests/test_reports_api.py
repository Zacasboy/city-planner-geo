"""Testes HTTP dos relatórios: autenticação e acesso só ao dono."""

from collections.abc import Callable, Iterator
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import reports_service

REPORT_BODY = {
    "beam_data": {
        "length": 5,
        "width": 0.3,
        "height": 0.5,
        "youngs_modulus": 200e9,
        "density": 7850,
        "yield_stress": 250e6,
        "point_loads": [{"position": 2.5, "magnitude": 10000}],
        "supports": [{"type": "pin", "position": 0}],
    },
    "analysis_results": {
        "max_deflection": 0.04,
        "max_stress": 1e6,
        "utilization_ratio": 0.004,
        "details": {},
    },
}
MISSING_ID = "99999999-9999-9999-9999-999999999999"


class FakeStorage:
    """Storage em memória com a API mínima usada pelo serviço."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def from_(self, _bucket: str) -> "FakeStorage":
        return self

    def upload(self, path: str, content: bytes, _options: dict[str, str]) -> None:
        self.files[path] = content

    def download(self, path: str) -> bytes:
        if path not in self.files:
            raise RuntimeError("Object not found")
        return self.files[path]

    def remove(self, paths: list[str]) -> list[dict[str, str]]:
        return [{"name": p} for p in paths if self.files.pop(p, None) is not None]


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeStorage]:
    fake = FakeStorage()
    monkeypatch.setattr(reports_service, "supabase", MagicMock(storage=fake))
    monkeypatch.setattr(
        reports_service.ReportsService, "_render_pdf", staticmethod(lambda _html: b"%PDF-fake")
    )
    yield fake


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _create(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/reports/structural", json=REPORT_BODY, headers=headers)
    assert response.status_code == 201
    report_id: str = response.json()["report_id"]
    return report_id


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/reports/structural"),
        ("get", f"/reports/{MISSING_ID}"),
        ("delete", f"/reports/{MISSING_ID}"),
    ],
)
def test_every_report_route_requires_authentication(
    client: TestClient, storage: FakeStorage, method: str, path: str
) -> None:
    kwargs: dict[str, Any] = {"json": REPORT_BODY} if method == "post" else {}
    assert getattr(client, method)(path, **kwargs).status_code in (401, 403)


def test_owner_can_create_download_and_delete(
    client: TestClient, storage: FakeStorage, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    headers = auth_headers("ana")
    report_id = _create(client, headers)
    assert list(storage.files) == [f"ana/{report_id}.pdf"]

    downloaded = client.get(f"/reports/{report_id}", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content == b"%PDF-fake"

    assert client.delete(f"/reports/{report_id}", headers=headers).status_code == 200
    assert storage.files == {}


def test_other_user_cannot_read_or_delete(
    client: TestClient, storage: FakeStorage, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    report_id = _create(client, auth_headers("ana"))
    rui = auth_headers("rui")

    assert client.get(f"/reports/{report_id}", headers=rui).status_code == 404
    assert client.delete(f"/reports/{report_id}", headers=rui).status_code == 404
    assert f"ana/{report_id}.pdf" in storage.files


def test_body_cannot_choose_the_owner(
    client: TestClient, storage: FakeStorage, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    body = REPORT_BODY | {"user_id": "rui"}
    response = client.post("/reports/structural", json=body, headers=auth_headers("ana"))
    assert response.status_code == 201
    assert all(path.startswith("ana/") for path in storage.files)


def test_report_id_must_be_a_uuid(
    client: TestClient, storage: FakeStorage, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    response = client.get("/reports/..%2F..%2Fana%2Fsegredo", headers=auth_headers("rui"))
    assert response.status_code in (404, 422)
    assert client.get("/reports/not-a-uuid", headers=auth_headers("rui")).status_code == 422


def test_token_subject_with_path_characters_is_rejected(
    client: TestClient, storage: FakeStorage, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    response = client.get(f"/reports/{MISSING_ID}", headers=auth_headers("../ana"))
    assert response.status_code == 401


def test_storage_errors_do_not_leak_details(
    client: TestClient, storage: FakeStorage, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    storage.download = MagicMock(side_effect=RuntimeError("https://x.supabase.co?key=segredo"))  # type: ignore[method-assign]
    response = client.get(f"/reports/{MISSING_ID}", headers=auth_headers("ana"))
    assert response.status_code == 500
    assert "segredo" not in response.text
