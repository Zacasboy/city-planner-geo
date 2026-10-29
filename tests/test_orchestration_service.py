"""
Tests for orchestration service with comprehensive mock tests.
"""

import os

# Set environment variables for required settings before importing the module
os.environ["SUPABASE_URL"] = "http://fake"
os.environ["SUPABASE_PUBLISHABLE_KEY"] = "fake"
os.environ["SUPABASE_SECRET_KEY"] = "fake"
os.environ["SECRET_KEY"] = "fakesecret"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

import uuid
from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.orchestration_service import OrchestrationService, TaskStatus


def test_orchestration_service_import():
    """Test that the orchestration service can be imported."""
    assert OrchestrationService is not None
    assert TaskStatus is not None


def test_task_status_model():
    """Test that TaskStatus model works."""
    status = TaskStatus(
        task_id="task123", status="SUCCESS", progress=1.0, result={"result": "ok"}, error=None
    )
    assert status.task_id == "task123"
    assert status.status == "SUCCESS"
    assert status.progress == 1.0
    assert status.result == {"result": "ok"}
    assert status.error is None


@pytest.mark.asyncio
async def test_orchestration_service_init():
    """Test orchestration service initialization."""
    service = OrchestrationService()
    assert service is not None
    assert service.celery_app is not None
    assert service.redis_client is not None


@pytest.mark.asyncio
async def test_submit_task_success():
    """Test successful task submission."""
    service = OrchestrationService()

    # Mock uuid.uuid4 to return a fixed task ID
    with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
        # Mock the Celery send_task method to avoid actual Celery execution
        with patch.object(service.celery_app, "send_task") as mock_send_task:
            # Configure the mock to return a mock task result (though we don't use its id)
            mock_task_result = MagicMock()
            mock_task_result.id = "unused-id"
            mock_send_task.return_value = mock_task_result

            # Mock the redis_client attribute
            with patch.object(service, "redis_client") as mock_redis:
                mock_redis.setex = MagicMock()

                task_id = await service.submit_task("test_task", {"param": "value"})

                # The service should return the fixed task id from uuid.uuid4
                expected_task_id = "12345678-1234-5678-1234-567812345678"
                assert task_id == expected_task_id
                mock_send_task.assert_called_once_with(
                    "tasks.test_task", args=[{"param": "value"}], task_id=expected_task_id
                )
                mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_get_task_status_success():
    """Test successful task status retrieval."""
    service = OrchestrationService()

    # Mock Redis to return a cached status
    cached_status = TaskStatus(
        task_id="test-task-id",
        status="SUCCESS",
        progress=1.0,
        result={"output": "task completed"},
        error=None,
    ).json()

    with patch.object(service, "redis_client") as mock_redis:
        mock_redis.get.return_value = cached_status

        status = await service.get_task_status("test-task-id")

        assert status.task_id == "test-task-id"
        assert status.status == "SUCCESS"
        assert status.progress == 1.0
        assert status.result == {"output": "task completed"}


@pytest.mark.asyncio
async def test_get_task_status_from_celery():
    """Test task status retrieval from Celery when not in Redis."""
    service = OrchestrationService()

    # Mock Redis to return None (not cached)
    with patch.object(service, "redis_client") as mock_redis:
        mock_redis.get.return_value = None
        # Mock Celery AsyncResult to return a completed task
        with patch.object(service.celery_app, "AsyncResult") as mock_async_result:
            # Configure the mock AsyncResult
            mock_result = MagicMock()
            mock_result.status = "SUCCESS"
            mock_result.result = {"data": "processed"}
            mock_result.ready.return_value = True
            mock_result.successful.return_value = True
            mock_async_result.return_value = mock_result

            status = await service.get_task_status("test-task-id")

            assert status.task_id == "test-task-id"
            assert status.status == "SUCCESS"
            assert status.progress == 1.0
            assert status.result == {"data": "processed"}


@pytest.mark.asyncio
async def test_submit_task_failure():
    """Test task submission handles errors."""
    service = OrchestrationService()

    # Mock the Celery send_task method to raise an exception
    with patch.object(service.celery_app, "send_task", side_effect=Exception("Celery error")):
        with pytest.raises(Exception) as exc_info:
            await service.submit_task("test_task", {"param": "value"})

        # Should raise HTTPException via the service's error handling
        assert "Celery error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_task_status_failure():
    """Test task status retrieval handles errors."""
    service = OrchestrationService()

    # Mock Redis to raise an exception
    with patch.object(service, "redis_client") as mock_redis:
        mock_redis.get.side_effect = Exception("Redis error")

        with pytest.raises(Exception) as exc_info:
            await service.get_task_status("test-task-id")

        # Should raise HTTPException via the service's error handling
        assert "Redis error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_orchestration_service_close():
    """Test that the service can be closed (does nothing)."""
    service = OrchestrationService()
    # Should not raise
    await service.close()


@pytest.mark.asyncio
async def test_task_status_model_validation():
    """Test TaskStatus model validation."""
    # Test valid status
    status = TaskStatus(
        task_id="test123", status="SUCCESS", progress=0.75, result={"data": "processed"}, error=None
    )
    assert status.task_id == "test123"
    assert status.status == "SUCCESS"
    assert status.progress == 0.75
    assert status.result == {"data": "processed"}
    assert status.error is None

    # Test with None progress and result
    status_none = TaskStatus(
        task_id="test456", status="PENDING", progress=None, result=None, error="Connection failed"
    )
    assert status_none.task_id == "test456"
    assert status_none.status == "PENDING"
    assert status_none.progress is None
    assert status_none.result is None
    assert status_none.error == "Connection failed"


@pytest.mark.asyncio
async def test_multiple_task_submissions():
    """Test submitting multiple tasks."""
    service = OrchestrationService()

    # Mock uuid.uuid4 to return fixed task IDs in sequence
    task_ids = [
        uuid.UUID("11111111-1111-1111-1111-111111111111"),
        uuid.UUID("22222222-2222-2222-2222-222222222222"),
        uuid.UUID("33333333-3333-3333-3333-333333333333"),
    ]
    with patch("uuid.uuid4") as mock_uuid:
        mock_uuid.side_effect = task_ids

        with patch.object(service.celery_app, "send_task") as mock_send_task:
            with patch.object(service, "redis_client") as mock_redis:
                mock_redis.setex = MagicMock()

                # Configure the mock to return dummy task results
                mock_send_task.side_effect = [
                    MagicMock(id="unused1"),
                    MagicMock(id="unused2"),
                    MagicMock(id="unused3"),
                ]

                # Submit three tasks
                task_id_1 = await service.submit_task("task_type_a", {"data": "first"})
                task_id_2 = await service.submit_task("task_type_b", {"data": "second"})
                task_id_3 = await service.submit_task("task_type_c", {"data": "third"})

                assert str(task_id_1) == "11111111-1111-1111-1111-111111111111"
                assert str(task_id_2) == "22222222-2222-2222-2222-222222222222"
                assert str(task_id_3) == "33333333-3333-3333-3333-333333333333"
                assert mock_send_task.call_count == 3
                assert mock_redis.setex.call_count == 3


@pytest.mark.asyncio
async def test_task_status_progress_values():
    """Test that progress values are correctly set based on status."""
    service = OrchestrationService()

    # Test different status values
    test_cases = [
        ("PENDING", 0.0),
        ("STARTED", 0.5),
        ("SUCCESS", 1.0),
        ("FAILURE", 1.0),
        ("RETRY", 0.5),
        ("REVOKED", 0.5),
        ("UNKNOWN", 0.5),  # Default for unknown status
    ]

    for status_val, expected_progress in test_cases:
        with patch.object(service, "redis_client") as mock_redis:
            mock_redis.get.return_value = None
            with patch.object(service.celery_app, "AsyncResult") as mock_async_result:
                # Configure the mock AsyncResult
                mock_result = MagicMock()
                mock_result.status = status_val
                mock_result.ready.return_value = True
                mock_result.successful.return_value = status_val == "SUCCESS"
                mock_result.result = {"test": "data"} if status_val == "SUCCESS" else None
                mock_async_result.return_value = mock_result

                status = await service.get_task_status("test-task-id")

                assert status.progress == expected_progress


@pytest.mark.asyncio
async def test_concurrent_task_handling():
    """Test handling of multiple concurrent tasks."""
    service = OrchestrationService()

    # Mock uuid.uuid4 to return fixed task IDs
    with patch("uuid.uuid4") as mock_uuid:
        mock_uuid.side_effect = [
            uuid.UUID("11111111-1111-1111-1111-111111111111"),
            uuid.UUID("22222222-2222-2222-2222-222222222222"),
        ]

        with patch.object(service.celery_app, "send_task") as mock_send_task:
            with patch.object(service, "redis_client") as mock_redis:
                mock_redis.get = MagicMock()
                mock_redis.setex = MagicMock()
                with patch.object(service.celery_app, "AsyncResult") as mock_async_result:
                    # Configure mocks
                    mock_send_task.side_effect = [MagicMock(id="unused1"), MagicMock(id="unused2")]

                    # First call returns cached status, second returns None (fetch from Celery)
                    mock_redis.get.side_effect = [
                        TaskStatus(
                            task_id="11111111-1111-1111-1111-111111111111",
                            status="SUCCESS",
                            progress=1.0,
                            result={"result": "done"},
                            error=None,
                        ).json(),
                        None,  # Second call returns None (not cached)
                    ]

                    # Configure Celery AsyncResult for second task
                    mock_result = MagicMock()
                    mock_result.status = "SUCCESS"
                    mock_result.result = {"output": "processed"}
                    mock_result.ready.return_value = True
                    mock_result.successful.return_value = True
                    mock_async_result.return_value = mock_result

                    # Submit and check status for both tasks
                    task_id_1 = await service.submit_task("task_type_a", {"data": "first"})
                    task_id_2 = await service.submit_task("task_type_b", {"data": "second"})

                    status_1 = await service.get_task_status(task_id_1)
                    status_2 = await service.get_task_status(task_id_2)

                    assert status_1.status == "SUCCESS"
                    assert status_1.result == {"result": "done"}
                    assert status_2.status == "SUCCESS"
                    assert status_2.result == {"output": "processed"}

                    # Verify calls
                    assert mock_send_task.call_count == 2
                    assert mock_redis.get.call_count == 2
                    assert mock_redis.setex.call_count == 3
                    assert mock_async_result.call_count == 1


@pytest.mark.asyncio
async def test_task_result_expiration():
    """Test that task results are handled correctly when expired."""
    service = OrchestrationService()

    with patch.object(service, "redis_client") as mock_redis:
        mock_redis.get.return_value = None
        with patch.object(service.celery_app, "AsyncResult") as mock_async_result:
            # Configure mock AsyncResult for expired task
            mock_result = MagicMock()
            mock_result.status = "SUCCESS"
            mock_result.result = {"data": "expired result"}
            mock_result.ready.return_value = True
            mock_result.successful.return_value = True
            mock_async_result.return_value = mock_result

            status = await service.get_task_status("expired-task-id")

            assert status.status == "SUCCESS"
            assert status.result == {"data": "expired result"}
            assert status.progress == 1.0
