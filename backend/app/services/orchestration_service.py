"""Orchestration Service - Celery + Redis Integration
T1.7: Orquestração: Celery + Redis, modelo de tarefa, GET /analysis/{id} com estado/progresso
"""

import logging
import uuid

from celery import Celery
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from redis import Redis

from backend.app.config import settings


class TaskStatus(BaseModel):
    """Model for task status."""

    task_id: str
    status: str  # e.g., PENDING, STARTED, SUCCESS, FAILURE
    progress: float | None = None  # 0.0 to 1.0
    result: dict | None = None
    error: str | None = None


# Create router
router = APIRouter()

# Configure logging
logger = logging.getLogger(__name__)


class OrchestrationService:
    """Service for Celery + Redis task orchestration."""

    def __init__(self):
        # Initialize Celery app
        self.celery_app = Celery(
            "city_planner", broker=settings.REDIS_URL, backend=settings.REDIS_URL
        )

        # Celery configuration updates
        self.celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
        )

        # Initialize Redis client for direct operations
        self.redis_client = Redis.from_url(settings.REDIS_URL)

    async def submit_task(self, task_type: str, payload: dict) -> str:
        """Submit a task for asynchronous processing.

        Args:
            task_type: Type of task to submit
            payload: Task payload data

        Returns:
            Task ID
        """
        try:
            # Generate a unique task ID
            task_id = str(uuid.uuid4())

            # Submit task to Celery
            task = self.celery_app.send_task(f"tasks.{task_type}", args=[payload], task_id=task_id)

            # Store initial status in Redis for quick access
            initial_status = TaskStatus(
                task_id=task_id, status="PENDING", progress=0.0, result=None, error=None
            )
            self.redis_client.setex(
                f"task:{task_id}", 3600, initial_status.json()  # Expire after 1 hour
            )

            logger.info(f"Submitted task {task_id} of type {task_type}")
            return task_id

        except Exception as e:
            logger.error(f"Failed to submit task: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to submit task: {str(e)}",
            )

    async def get_task_status(self, task_id: str) -> TaskStatus:
        """Get status of a task.

        Args:
            task_id: Task ID

        Returns:
            TaskStatus with current status and progress
        """
        try:
            # First check Redis for cached status
            cached_status = self.redis_client.get(f"task:{task_id}")
            if cached_status:
                return TaskStatus.parse_raw(cached_status)

            # If not in Redis, check Celery
            task_result = self.celery_app.AsyncResult(task_id)

            # Get Celery status (uppercase string like 'SUCCESS', 'FAILURE', etc.)
            celery_status = task_result.status

            # Get result if available
            result_data = None
            error_msg = None

            if task_result.ready():
                if task_result.successful():
                    result_data = task_result.result
                else:
                    error_msg = str(task_result.result)

            # Map status to progress
            progress_map = {
                "PENDING": 0.0,
                "STARTED": 0.5,
                "SUCCESS": 1.0,
                "FAILURE": 1.0,
                "RETRY": 0.5,
                "REVOKED": 0.5,
                "UNKNOWN": 0.5,
            }
            progress = progress_map.get(celery_status, 0.0)

            # Create status object
            task_status = TaskStatus(
                task_id=task_id,
                status=celery_status,
                progress=progress,
                result=result_data,
                error=error_msg,
            )

            # Cache the status for future requests
            self.redis_client.setex(
                f"task:{task_id}", 3600, task_status.json()  # Expire after 1 hour
            )

            return task_status

        except Exception as e:
            logger.error(f"Failed to get task status: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get task status: {str(e)}",
            )

    async def close(self):
        """Close the service (no-op)."""
        pass


# Create service instance
orchestration_service = OrchestrationService()


# Convenience functions
async def submit_task(task_type: str, payload: dict) -> str:
    """Submit a task for asynchronous processing."""
    return await orchestration_service.submit_task(task_type, payload)


async def get_task_status(task_id: str) -> TaskStatus:
    """Get status of a task."""
    return await orchestration_service.get_task_status(task_id)


# API Routes
@router.post("/tasks/{task_type}", tags=["orchestration"])
async def submit_task_endpoint(task_type: str, payload: dict):
    """Submit a task for asynchronous processing.

    Args:
        task_type: Type of task to submit
        payload: Task payload data

    Returns:
        Task ID
    """
    try:
        return await submit_task(task_type, payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit task: {str(e)}",
        )


@router.get("/analysis/{task_id}", tags=["orchestration"])
async def get_analysis_status_endpoint(task_id: str):
    """Get status of an analysis task.

    Args:
        task_id: Task ID

    Returns:
        Task status and progress
    """
    try:
        return await get_task_status(task_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}",
        )
