"""Orquestração de tarefas com Celery e Redis.

T1.7: modelo de tarefa e `GET /analysis/{id}` com estado e progresso.
Cada tarefa pertence ao utilizador que a submeteu; os outros recebem 404.
"""

import logging
import re
import uuid
from typing import Annotated, Any

from celery import Celery
from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel
from redis import Redis

from backend.app.auth import CurrentUserId
from backend.app.config import settings

logger = logging.getLogger(__name__)

TASK_TYPE_PATTERN = r"^[a-z][a-z0-9_]{0,63}$"
STATUS_CACHE_TTL_S = 3600
# O Celery guarda os resultados 1 dia por omissão; o dono tem de durar o mesmo.
TASK_OWNER_TTL_S = 86400
# Só estados finais podem ir para a cache: um estado intermédio ficaria desatualizado.
TERMINAL_STATES = frozenset({"SUCCESS", "FAILURE"})
PROGRESS_BY_STATE = {
    "PENDING": 0.0,
    "STARTED": 0.5,
    "SUCCESS": 1.0,
    "FAILURE": 1.0,
    "RETRY": 0.5,
    "REVOKED": 0.5,
    "UNKNOWN": 0.5,
}


class TaskStatus(BaseModel):
    """Estado de uma tarefa."""

    task_id: str
    status: str  # PENDING, STARTED, SUCCESS, FAILURE, ...
    progress: float | None = None  # 0.0 a 1.0
    result: dict[str, Any] | None = None
    error: str | None = None


router = APIRouter()


def _status_key(task_id: str) -> str:
    return f"task:{task_id}"


def _owner_key(task_id: str) -> str:
    return f"task_owner:{task_id}"


def _as_text(value: bytes | str) -> str:
    return value.decode() if isinstance(value, bytes) else value


class OrchestrationService:
    """Submissão e consulta de tarefas Celery, com estado em Redis."""

    def __init__(self) -> None:
        """Cria a aplicação Celery e o cliente Redis."""
        self.celery_app = Celery(
            "city_planner", broker=settings.REDIS_URL, backend=settings.REDIS_URL
        )
        self.celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
        )
        self.redis_client = Redis.from_url(settings.REDIS_URL)

    async def submit_task(self, task_type: str, payload: dict[str, Any], owner_id: str) -> str:
        """Submete uma tarefa para processamento assíncrono.

        Args:
            task_type: Tipo de tarefa (minúsculas, dígitos e `_`).
            payload: Dados da tarefa.
            owner_id: Utilizador que submete; só ele consegue consultar o estado.

        Returns:
            Identificador da tarefa.

        Raises:
            HTTPException: 422 se o tipo for inválido, 500 se a submissão falhar.
        """
        if not re.fullmatch(TASK_TYPE_PATTERN, task_type):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid task type"
            )
        task_id = str(uuid.uuid4())
        try:
            self.redis_client.setex(_owner_key(task_id), TASK_OWNER_TTL_S, owner_id)
            self.celery_app.send_task(f"tasks.{task_type}", args=[payload], task_id=task_id)
        except Exception as e:
            logger.error("Failed to submit task: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit task",
            ) from e
        logger.info("Submitted task %s of type %s", task_id, task_type)
        return task_id

    async def get_task_status(self, task_id: str, owner_id: str) -> TaskStatus:
        """Devolve o estado de uma tarefa do utilizador.

        Args:
            task_id: Identificador da tarefa.
            owner_id: Utilizador que consulta.

        Returns:
            Estado e progresso da tarefa.

        Raises:
            HTTPException: 404 se a tarefa não existir ou for de outro utilizador,
                500 se a consulta falhar.
        """
        try:
            stored_owner = self.redis_client.get(_owner_key(task_id))
            if stored_owner is None or _as_text(stored_owner) != owner_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
            cached = self.redis_client.get(_status_key(task_id))
            if cached:
                return TaskStatus.model_validate_json(cached)
            return self._status_from_celery(task_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get task status: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get task status",
            ) from e

    def _status_from_celery(self, task_id: str) -> TaskStatus:
        task_result = self.celery_app.AsyncResult(task_id)
        celery_status = task_result.status
        result_data = None
        error_msg = None
        if task_result.ready():
            if task_result.successful():
                result_data = task_result.result
            else:
                error_msg = str(task_result.result)

        task_status = TaskStatus(
            task_id=task_id,
            status=celery_status,
            progress=PROGRESS_BY_STATE.get(celery_status, 0.0),
            result=result_data,
            error=error_msg,
        )
        if celery_status in TERMINAL_STATES:
            self.redis_client.setex(
                _status_key(task_id), STATUS_CACHE_TTL_S, task_status.model_dump_json()
            )
        return task_status

    async def close(self) -> None:
        """Fecha o serviço (não faz nada por agora)."""


orchestration_service = OrchestrationService()


async def submit_task(task_type: str, payload: dict[str, Any], owner_id: str) -> str:
    """Submete uma tarefa para processamento assíncrono."""
    return await orchestration_service.submit_task(task_type, payload, owner_id)


async def get_task_status(task_id: str, owner_id: str) -> TaskStatus:
    """Devolve o estado de uma tarefa."""
    return await orchestration_service.get_task_status(task_id, owner_id)


@router.post("/tasks/{task_type}", tags=["orchestration"])
async def submit_task_endpoint(
    task_type: Annotated[str, Path(pattern=TASK_TYPE_PATTERN)],
    payload: dict[str, Any],
    user_id: CurrentUserId,
) -> str:
    """Submete uma tarefa para processamento assíncrono.

    Args:
        task_type: Tipo de tarefa.
        payload: Dados da tarefa.
        user_id: Utilizador autenticado.

    Returns:
        Identificador da tarefa.
    """
    return await submit_task(task_type, payload, user_id)


@router.get("/analysis/{task_id}", tags=["orchestration"])
async def get_analysis_status_endpoint(task_id: str, user_id: CurrentUserId) -> TaskStatus:
    """Devolve o estado e o progresso de uma tarefa de análise.

    Args:
        task_id: Identificador da tarefa.
        user_id: Utilizador autenticado.

    Returns:
        Estado e progresso da tarefa.
    """
    return await get_task_status(task_id, user_id)
