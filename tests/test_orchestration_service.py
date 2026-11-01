"""Testes da orquestração: dono da tarefa, estados e cache."""

import json
from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.orchestration_service import OrchestrationService, TaskStatus


class FakeRedis:
    """Redis em memória, só com o que o serviço usa."""

    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.data[key] = value.encode()
        self.ttls[key] = ttl

    def get(self, key: str) -> bytes | None:
        return self.data.get(key)


def _celery_result(state: str, result: object = None) -> SimpleNamespace:
    return SimpleNamespace(
        status=state,
        result=result,
        ready=lambda: state in ("SUCCESS", "FAILURE"),
        successful=lambda: state == "SUCCESS",
    )


@pytest.fixture
def service() -> OrchestrationService:
    svc = OrchestrationService()
    svc.redis_client = FakeRedis()  # type: ignore[assignment]
    svc.celery_app = MagicMock()
    return svc


def test_task_status_model() -> None:
    status = TaskStatus(task_id="t", status="SUCCESS", progress=1.0, result={"a": 1})
    assert status.result == {"a": 1}
    assert status.error is None


@pytest.mark.asyncio
async def test_submit_sends_task_and_records_owner(service: OrchestrationService) -> None:
    task_id = await service.submit_task("analysis", {"x": 1}, owner_id="ana")
    service.celery_app.send_task.assert_called_once_with(
        "tasks.analysis", args=[{"x": 1}], task_id=task_id
    )
    assert service.redis_client.data[f"task_owner:{task_id}"] == b"ana"


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_type", ["../etc", "Analysis", "a b", "", "x" * 65, "1abc"])
async def test_submit_rejects_invalid_task_type(
    service: OrchestrationService, bad_type: str
) -> None:
    with pytest.raises(HTTPException) as info:
        await service.submit_task(bad_type, {}, owner_id="ana")
    assert info.value.status_code == 422
    service.celery_app.send_task.assert_not_called()


@pytest.mark.asyncio
async def test_submit_failure_is_500_without_internal_details(
    service: OrchestrationService,
) -> None:
    service.celery_app.send_task.side_effect = RuntimeError("redis://user:senha@host")
    with pytest.raises(HTTPException) as info:
        await service.submit_task("analysis", {}, owner_id="ana")
    assert info.value.status_code == 500
    assert "senha" not in str(info.value.detail)


@pytest.mark.asyncio
async def test_other_user_gets_404(service: OrchestrationService) -> None:
    task_id = await service.submit_task("analysis", {}, owner_id="ana")
    with pytest.raises(HTTPException) as info:
        await service.get_task_status(task_id, owner_id="rui")
    assert info.value.status_code == 404


@pytest.mark.asyncio
async def test_unknown_task_gets_404(service: OrchestrationService) -> None:
    with pytest.raises(HTTPException) as info:
        await service.get_task_status("nao-existe", owner_id="ana")
    assert info.value.status_code == 404


@pytest.mark.asyncio
async def test_pending_task_is_not_cached_so_completion_is_seen(
    service: OrchestrationService,
) -> None:
    task_id = await service.submit_task("analysis", {}, owner_id="ana")

    service.celery_app.AsyncResult.return_value = _celery_result("PENDING")
    first = await service.get_task_status(task_id, "ana")
    assert (first.status, first.progress) == ("PENDING", 0.0)

    service.celery_app.AsyncResult.return_value = _celery_result("SUCCESS", {"ok": True})
    second = await service.get_task_status(task_id, "ana")
    assert (second.status, second.progress, second.result) == ("SUCCESS", 1.0, {"ok": True})


@pytest.mark.asyncio
async def test_final_state_is_cached_and_served_from_cache(
    service: OrchestrationService,
) -> None:
    task_id = await service.submit_task("analysis", {}, owner_id="ana")
    service.celery_app.AsyncResult.return_value = _celery_result("SUCCESS", {"ok": True})
    await service.get_task_status(task_id, "ana")
    assert f"task:{task_id}" in service.redis_client.data

    service.celery_app.AsyncResult.reset_mock()
    cached = await service.get_task_status(task_id, "ana")
    assert cached.result == {"ok": True}
    service.celery_app.AsyncResult.assert_not_called()


@pytest.mark.asyncio
async def test_failure_reports_error_and_progress(service: OrchestrationService) -> None:
    task_id = await service.submit_task("analysis", {}, owner_id="ana")
    service.celery_app.AsyncResult.return_value = _celery_result("FAILURE", ValueError("boom"))
    result = await service.get_task_status(task_id, "ana")
    assert (result.status, result.error, result.progress) == ("FAILURE", "boom", 1.0)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "progress"), [("STARTED", 0.5), ("RETRY", 0.5), ("REVOKED", 0.5), ("OTHER", 0.0)]
)
async def test_progress_by_state(
    service: OrchestrationService, state: str, progress: float
) -> None:
    task_id = await service.submit_task("analysis", {}, owner_id="ana")
    service.celery_app.AsyncResult.return_value = _celery_result(state)
    assert (await service.get_task_status(task_id, "ana")).progress == progress


@pytest.mark.asyncio
async def test_status_failure_is_500_without_internal_details(
    service: OrchestrationService,
) -> None:
    service.redis_client = MagicMock()
    service.redis_client.get.side_effect = ConnectionError("redis://user:senha@host")
    with pytest.raises(HTTPException) as info:
        await service.get_task_status("t", "ana")
    assert info.value.status_code == 500
    assert "senha" not in str(info.value.detail)


@pytest.mark.asyncio
async def test_close_is_a_no_op(service: OrchestrationService) -> None:
    await service.close()


def test_endpoints_require_authentication() -> None:
    client = TestClient(app)
    assert client.post("/orchestration/tasks/analysis", json={}).status_code in (401, 403)
    assert client.get("/orchestration/analysis/abc").status_code in (401, 403)


def test_endpoints_enforce_ownership_and_task_type(
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    fake = FakeRedis()
    celery = MagicMock()
    celery.AsyncResult.return_value = _celery_result("STARTED")
    client = TestClient(app)
    with (patch("backend.app.services.orchestration_service.orchestration_service") as svc_patch,):
        real = OrchestrationService()
        real.redis_client = fake  # type: ignore[assignment]
        real.celery_app = celery
        svc_patch.submit_task = real.submit_task
        svc_patch.get_task_status = real.get_task_status

        created = client.post(
            "/orchestration/tasks/analysis", json={"a": 1}, headers=auth_headers("ana")
        )
        assert created.status_code == 200
        task_id = json.loads(created.text)

        own = client.get(f"/orchestration/analysis/{task_id}", headers=auth_headers("ana"))
        other = client.get(f"/orchestration/analysis/{task_id}", headers=auth_headers("rui"))
        bad_type = client.post(
            "/orchestration/tasks/Bad-Type", json={}, headers=auth_headers("ana")
        )

    assert own.status_code == 200
    assert own.json()["status"] == "STARTED"
    assert other.status_code == 404
    assert bad_type.status_code == 422
