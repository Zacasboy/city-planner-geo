"""Rotas da API de morfologia urbana.

T2.1: OpenBuildingMap/DBSM e métricas (densidade, altura, ocupação).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from backend.app.auth import get_current_user
from backend.app.services.morphology_service import (
    MorphologyRequest,
    MorphologyResponse,
    MorphologyService,
)

router = APIRouter(prefix="/morphology", tags=["morphology"])

morphology_service = MorphologyService()


@router.post("/analyze", response_model=MorphologyResponse)
async def analyze_morphology(
    request: MorphologyRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> MorphologyResponse:
    """Analisa a morfologia dos edifícios de uma área.

    Args:
        request: GeoJSON da área e parâmetros da análise.
        current_user: Utilizador autenticado.

    Returns:
        Métricas de morfologia da área.
    """
    return await morphology_service.analyze_morphology(request)
