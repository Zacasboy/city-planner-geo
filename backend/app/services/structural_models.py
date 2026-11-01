"""Modelos de entrada e saída da análise de vigas (unidades SI: m, N, Pa, kg/m³)."""

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

SupportType = Literal["pin", "roller", "fixed"]
POSITION_TOLERANCE_M = 1e-9


class PointLoad(BaseModel):
    """Carga pontual vertical."""

    position: float = Field(..., ge=0, description="Position in meters from the left end")
    magnitude: float = Field(..., description="Force in N, positive downward")


class Support(BaseModel):
    """Apoio no plano da viga: `pin` (fixa a posição), `roller` ou `fixed` (encastramento)."""

    position: float = Field(..., ge=0, description="Position in meters from the left end")
    type: SupportType


class BeamRequest(BaseModel):
    """Pedido de análise de uma viga de aço de secção retangular."""

    length: float = Field(..., gt=0, description="Beam length in meters")
    width: float = Field(..., gt=0, description="Cross-section width in meters")
    height: float = Field(..., gt=0, description="Cross-section height in meters")
    youngs_modulus: float = Field(..., gt=0, description="Young's modulus in Pa")
    density: float = Field(..., gt=0, description="Material density in kg/m^3")
    yield_stress: float = Field(..., gt=0, description="Yield stress in Pa")
    poisson_ratio: float = Field(default=0.3, gt=0, lt=0.5)
    point_loads: list[PointLoad] = Field(default_factory=list)
    uniform_load: float = Field(
        default=0.0, description="Uniform load over the whole beam in N/m, positive downward"
    )
    include_self_weight: bool = Field(default=True, description="Add the beam's own weight")
    supports: list[Support] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _check_geometry_and_stability(self) -> Self:
        """Garante cargas e apoios dentro da viga e uma viga estável (sem corpo rígido)."""
        items: list[PointLoad | Support] = [*self.point_loads, *self.supports]
        for item in items:
            if item.position > self.length + POSITION_TOLERANCE_M:
                raise ValueError(
                    f"Position {item.position} m is outside the beam (0 to {self.length} m)"
                )
        positions = sorted(s.position for s in self.supports)
        if any(
            b - a <= POSITION_TOLERANCE_M for a, b in zip(positions, positions[1:], strict=False)
        ):
            raise ValueError("Two supports cannot be at the same position")
        has_fixed = any(s.type == "fixed" for s in self.supports)
        if not has_fixed and (
            len(self.supports) < 2 or not any(s.type == "pin" for s in self.supports)
        ):
            raise ValueError(
                "The beam is unstable: use a fixed support, or two supports including one pin"
            )
        return self


class BeamResponse(BaseModel):
    """Resultado da análise de uma viga."""

    max_deflection: float = Field(..., description="Maximum deflection in meters (absolute value)")
    max_stress: float = Field(
        ..., description="Maximum bending stress in Pa (absolute value, extreme fibre)"
    )
    utilization_ratio: float = Field(
        ..., description="Utilization ratio (max_stress / yield_stress)"
    )
    details: dict[str, Any] = Field(..., description="Additional analysis details")
