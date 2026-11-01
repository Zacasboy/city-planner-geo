"""Análise de vigas de aço.

T1.6: viga simplesmente apoiada com carga pontual, com fórmulas analíticas.
A análise por elementos finitos (PyNite) e a validação com TimoDS ficam por fazer.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter()

logger = logging.getLogger(__name__)

EXPECTED_SUPPORTS = 2
ANALYSIS_METHOD = "Analytical (simply supported beam with point load at midspan)"
RESULT_NOTE = (
    "For multiple point loads not at midspan, results are approximate. "
    "For distributed loads, not implemented."
)


class BeamRequest(BaseModel):
    """Pedido de análise de uma viga de aço."""

    length: float = Field(..., gt=0, description="Beam length in meters")
    width: float = Field(..., gt=0, description="Cross-section width in meters")
    height: float = Field(..., gt=0, description="Cross-section height in meters")
    youngs_modulus: float = Field(..., gt=0, description="Young's modulus in Pa")
    density: float = Field(..., gt=0, description="Material density in kg/m^3")
    yield_stress: float = Field(..., gt=0, description="Yield stress in Pa")
    point_loads: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "List of point loads, each with 'position' (m from left) "
            "and 'magnitude' (N, positive downward)"
        ),
    )
    supports: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "List of supports, each with 'position' (m from left) " "and 'type' ('pin' or 'roller')"
        ),
    )


class BeamResponse(BaseModel):
    """Resultado da análise de uma viga."""

    max_deflection: float = Field(
        ..., description="Maximum deflection in meters (positive downward)"
    )
    max_stress: float = Field(
        ..., description="Maximum bending stress in Pa (positive for tension)"
    )
    utilization_ratio: float = Field(
        ..., description="Utilization ratio (max_stress / yield_stress)"
    )
    details: dict[str, Any] = Field(..., description="Additional analysis details")


def _midspan_point_load_results(
    load_n: float, length_m: float, youngs_modulus: float, inertia_m4: float, fiber_m: float
) -> tuple[float, float]:
    """Flecha e tensão máximas de uma viga simplesmente apoiada com carga a meio vão."""
    if load_n == 0:
        return 0.0, 0.0
    deflection = load_n * length_m**3 / (48 * youngs_modulus * inertia_m4)
    max_moment = load_n * length_m / 4
    return deflection, max_moment * fiber_m / inertia_m4


class StructuralService:
    """Análise de vigas de aço por fórmulas analíticas."""

    async def close(self) -> None:
        """Fecha o serviço (não faz nada por agora)."""

    async def analyze_beam(self, request: BeamRequest) -> BeamResponse:
        """Analisa uma viga simplesmente apoiada.

        A soma de todas as cargas pontuais é aplicada a meio vão, o que é conservador
        para a flecha e o momento máximos. As posições dos apoios são ignoradas.

        Args:
            request: Geometria, material, cargas e apoios da viga.

        Returns:
            Flecha máxima, tensão máxima e taxa de utilização.

        Raises:
            HTTPException: 500 se a análise falhar.
        """
        try:
            return self._analyze(request)
        except Exception as e:
            logger.error("Beam analysis failed: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Beam analysis failed: {e}",
            ) from e

    def _analyze(self, request: BeamRequest) -> BeamResponse:
        area_m2 = request.width * request.height
        inertia_m4 = request.width * request.height**3 / 12
        fiber_m = request.height / 2

        if len(request.supports) != EXPECTED_SUPPORTS:
            logger.warning(
                "Expected 2 supports, got %d. Assuming simply supported beam at the ends.",
                len(request.supports),
            )
        if len(request.point_loads) > 1:
            logger.warning(
                "Multiple point loads (%d) detected. Using total load at midspan. "
                "Results may be conservative.",
                len(request.point_loads),
            )
        total_load_n = sum(load.get("magnitude", 0.0) for load in request.point_loads)

        deflection, stress = _midspan_point_load_results(
            total_load_n, request.length, request.youngs_modulus, inertia_m4, fiber_m
        )
        return BeamResponse(
            max_deflection=deflection,
            max_stress=stress,
            utilization_ratio=stress / request.yield_stress,
            details={
                "beam_length_m": request.length,
                "cross_section_width_m": request.width,
                "cross_section_height_m": request.height,
                "cross_section_area_m2": area_m2,
                "moment_of_inertia_m4": inertia_m4,
                "youngs_modulus_pa": request.youngs_modulus,
                "density_kgm3": request.density,
                "yield_stress_pa": request.yield_stress,
                "total_point_load_n": total_load_n,
                "analysis_method": ANALYSIS_METHOD,
                "note": RESULT_NOTE,
            },
        )


structural_service = StructuralService()


async def analyze_beam(request: BeamRequest) -> BeamResponse:
    """Analisa uma viga de aço."""
    return await structural_service.analyze_beam(request)


@router.post("/beam", tags=["structural"])
async def structural_beam_endpoint(request: BeamRequest) -> BeamResponse:
    """Analisa uma viga de aço com fórmulas analíticas.

    Args:
        request: Geometria, material, cargas e apoios da viga.

    Returns:
        Resultados da análise.
    """
    return await analyze_beam(request)
