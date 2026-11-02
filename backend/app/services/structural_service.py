"""Análise de vigas de aço.

T1.6: elementos finitos de Timoshenko com apoios, cargas pontuais, carga uniforme e peso próprio,
validados contra soluções analíticas fechadas (tests/test_structural_service.py).
A validação com o benchmark TimoDS (flexão e axial, erro < 0,011 %) está em `timods_benchmark`.
A torção não é suportada.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from backend.app.services.structural_fem import solve_beam
from backend.app.services.structural_models import BeamRequest, BeamResponse

router = APIRouter()

logger = logging.getLogger(__name__)

ANALYSIS_METHOD = "FEM: Timoshenko beam, linear elastic, bending in one plane"
ANALYSIS_METHOD_EULER = "FEM: Euler-Bernoulli beam, linear elastic, bending in one plane"
RESULT_NOTE = (
    "Preliminary estimate of bending only: it ignores torsion, lateral-torsional buckling, "
    "local effects and code checks (Eurocode). It does not replace a structural design."
)


class StructuralService:
    """Análise de vigas de aço por fórmulas analíticas."""

    async def close(self) -> None:
        """Fecha o serviço (não faz nada por agora)."""

    async def analyze_beam(self, request: BeamRequest) -> BeamResponse:
        """Analisa uma viga por elementos finitos.

        Args:
            request: Geometria, material, cargas e apoios da viga.

        Returns:
            Flecha máxima, tensão de flexão máxima e taxa de utilização.

        Raises:
            HTTPException: 500 se a análise falhar.
        """
        try:
            return self._analyze(request)
        except Exception as e:
            logger.error("Beam analysis failed: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Beam analysis failed",
            ) from e

    def _analyze(self, request: BeamRequest) -> BeamResponse:
        results = solve_beam(request)
        area_m2 = request.area
        inertia_m4 = request.inertia
        stress_pa = results.max_moment_nm * (request.depth / 2) / inertia_m4
        return BeamResponse(
            max_deflection=results.max_deflection_m,
            max_stress=stress_pa,
            utilization_ratio=stress_pa / request.yield_stress,
            details={
                "beam_length_m": request.length,
                "cross_section_height_m": request.depth,
                "shear_area_m2": request.shear_area,
                "cross_section_area_m2": area_m2,
                "moment_of_inertia_m4": inertia_m4,
                "youngs_modulus_pa": request.youngs_modulus,
                "density_kgm3": request.density,
                "yield_stress_pa": request.yield_stress,
                "self_weight_n_per_m": results.self_weight_n_per_m,
                "total_load_n": results.total_load_n,
                "max_bending_moment_nm": results.max_moment_nm,
                "max_shear_force_n": results.max_shear_n,
                "reactions_n": {str(x): r for x, r in results.reactions_n.items()},
                "analysis_method": (
                    ANALYSIS_METHOD if request.include_shear_deformation else ANALYSIS_METHOD_EULER
                ),
                "note": RESULT_NOTE,
            },
        )


structural_service = StructuralService()


async def analyze_beam(request: BeamRequest) -> BeamResponse:
    """Analisa uma viga de aço."""
    return await structural_service.analyze_beam(request)


@router.post("/beam", tags=["structural"])
async def structural_beam_endpoint(request: BeamRequest) -> BeamResponse:
    """Analisa uma viga de aço por elementos finitos.

    Args:
        request: Geometria, material, cargas e apoios da viga.

    Returns:
        Resultados da análise.
    """
    return await analyze_beam(request)
