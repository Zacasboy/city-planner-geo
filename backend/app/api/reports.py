"""Rotas da API de relatórios.

T1.12: relatório PDF (Jinja2 + WeasyPrint, upload para Storage, `GET /reports/{id}`).
Todas as rotas exigem autenticação e só dão acesso aos relatórios do próprio utilizador.
"""

import io
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.app.auth import CurrentUserId
from backend.app.services.reports_service import ReportNotFoundError, ReportsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])

reports_service = ReportsService()


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")


class StructuralReportRequest(BaseModel):
    """Request model for generating a structural analysis report."""

    beam_data: dict[str, Any]
    analysis_results: dict[str, Any]


def _internal_error(action: str, error: Exception) -> HTTPException:
    logger.error("Failed to %s: %s", action, error, exc_info=True)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to {action}"
    )


@router.post("/structural", status_code=status.HTTP_201_CREATED)
async def generate_structural_report(
    request: StructuralReportRequest, user_id: CurrentUserId
) -> dict[str, str]:
    """Gera o relatório PDF de uma análise de viga e guarda-o para o utilizador.

    Args:
        request: Dados da viga e resultados da análise.
        user_id: Utilizador autenticado, dono do relatório.

    Returns:
        O identificador do relatório e o URL de descarga.
    """
    try:
        report_id = await reports_service.generate_structural_report(
            beam_data=request.beam_data,
            analysis_results=request.analysis_results,
            user_id=user_id,
        )
    except Exception as e:
        raise _internal_error("generate report", e) from e
    return {
        "report_id": report_id,
        "message": "Report generated successfully",
        "download_url": f"/reports/{report_id}",
    }


@router.get("/{report_id}")
async def get_report(report_id: UUID, user_id: CurrentUserId) -> StreamingResponse:
    """Devolve o PDF de um relatório do utilizador.

    Args:
        report_id: Identificador do relatório.
        user_id: Utilizador autenticado.

    Returns:
        O ficheiro PDF.
    """
    try:
        pdf_bytes = await reports_service.get_report(str(report_id), user_id)
    except ReportNotFoundError as e:
        raise _not_found() from e
    except Exception as e:
        raise _internal_error("retrieve report", e) from e
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=report_{report_id}.pdf"},
    )


@router.delete("/{report_id}", status_code=status.HTTP_200_OK)
async def delete_report(report_id: UUID, user_id: CurrentUserId) -> dict[str, str]:
    """Apaga um relatório do utilizador.

    Args:
        report_id: Identificador do relatório.
        user_id: Utilizador autenticado.

    Returns:
        Mensagem de confirmação.
    """
    try:
        await reports_service.delete_report(str(report_id), user_id)
    except ReportNotFoundError as e:
        raise _not_found() from e
    except Exception as e:
        raise _internal_error("delete report", e) from e
    return {"message": f"Report {report_id} deleted successfully"}
