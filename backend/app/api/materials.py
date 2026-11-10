"""Rotas da API do catálogo de materiais (T2.3)."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from backend.app.services import materials_service
from backend.app.services.materials_models import (
    Basis,
    CarbonMetric,
    Category,
    Exposure,
    SortBy,
    SuggestResponse,
)

router = APIRouter()

MAX_RESULTS = 50


def parse_costs(raw: list[str]) -> dict[str, float]:
    """Converte ``id:valor`` em custos por material.

    Raises:
        HTTPException: Se algum custo não tiver o formato ``id:valor`` com valor >= 0.
    """
    costs: dict[str, float] = {}
    for item in raw:
        material_id, separator, value = item.partition(":")
        try:
            number = float(value)
        except ValueError:
            number = -1.0
        if not separator or not material_id or number < 0:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid cost '{item}': use material-id:value with value >= 0",
            )
        costs[material_id] = number
    return costs


@router.get("/suggest", response_model=SuggestResponse)
async def suggest(
    category: Category,
    basis: Basis = "per_m3",
    carbon_metric: CarbonMetric = "fossil",
    sort: SortBy = "carbon",
    exposure: Exposure = "general",
    cost: Annotated[
        list[str] | None, Query(description="material-id:value (your own costs)")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_RESULTS)] = MAX_RESULTS,
) -> SuggestResponse:
    """Sugere materiais de uma categoria ordenados por pegada de carbono A1-A3 (ÖKOBAUDAT).

    Args:
        category: Categoria do material.
        basis: Por kg, por m3 ou por m2.
        carbon_metric: ``fossil`` (por omissão) ou ``total`` (com carbono biogénico).
        sort: Ordenar por carbono ou pelos custos indicados.
        exposure: Notas normativas para exposição húmida ou costeira.
        cost: Custos do utilizador, um por material, no formato ``id:valor``.
        limit: Número máximo de resultados.

    Returns:
        Os materiais ordenados, com dataset de origem, avisos e licença da fonte.
    """
    return materials_service.suggest_materials(
        category, basis, carbon_metric, sort, exposure, parse_costs(cost or []), limit
    )
