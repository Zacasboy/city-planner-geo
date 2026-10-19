"""
Tests for orchestration service.
"""
import os
# Set environment variables for required settings before importing the module
os.environ["SUPABASE_URL"] = "http://fake"
os.environ["SUPABASE_ANON_KEY"] = "fake"
os.environ["SUPABASE_SERVICE_KEY"] = "fake"
os.environ["SECRET_KEY"] = "fakesecret"

import pytest
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