"""
Tests for orchestration service with comprehensive mock tests.
"""
import os
# Set environment variables for required settings before importing the module
os.environ["SUPABASE_URL"] = "http://fake"
os.environ["SUPABASE_ANON_KEY"] = "fake"
os.environ["SUPABASE_SERVICE_KEY"] = "fake"
os.environ["SECRET_KEY"] = "fakesecret"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.orchestration_service import OrchestrationService, TaskStatus

def test_orchestration_service_import():
    """Test that the orchestration service can be imported."""
    assert OrchestrationService is not None
    assert TaskStatus is not None

def test_task_status_model():
    """Test that TaskStatus model works."""
    status = TaskStatus(
        task_id="task123",
        status="SUCCESS",
        progress=1.0,
        result={"result": "ok"},
        error=None
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

    # Mock the Celery send_task method to avoid actual Celery execution
    with patch.object(service.celery_app, 'send_task') as mock_send_task:
        # Configure the mock to return a mock task result
        mock_task_result = MagicMock()
        mock_task_result.id = "test-task-id-123"
        mock_send_task.return_value = mock_task_result

        # Also mock the Redis setex method
        with patch.object(service.redis_client, 'setex') as mock_setex:
            task_id = await service.submit_task("test_task", {"param": "value"})

            assert task_id == "test-task-id-123"
            mock_send_task.assert_called_once_with(
                'tasks.test_task',
                args=[{"param": "value"}],
                task_id="test-task-id-123"
            )
            mock_setex.assert_called_once()

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
        error=None
    ).json()

    with patch.object(service.redis_client, 'get', return_value=cached_status):
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
    # Mock Celery AsyncResult to return a completed task
    with patch.object(service.redis_client, 'get', return_value=None):
        with patch('backend.app.services.orchestration_service.celery_app.AsyncResult') as mock_async_result:
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
    with patch.object(service.celery_app, 'send_task', side_effect=Exception("Celery error")):
        with pytest.raises(Exception) as exc_info:
            await service.submit_task("test_task", {"param": "value"})

        # Should raise HTTPException via the service's error handling
        assert "Celery error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_task_status_failure():
    """Test task status retrieval handles errors."""
    service = OrchestrationService()

    # Mock Redis to raise an exception
    with patch.object(service.redis_client, 'get', side_effect=Exception("Redis error")):
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