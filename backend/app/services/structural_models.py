"""Modelos de entrada e saída da análise de vigas (unidades SI: m, N, Pa, kg/m³)."""

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

SupportType = Literal["pin", "roller", "fixed"]
POSITION_TOLERANCE_M = 1e-9
SECTION_SHEAR_FRACTION = 0.5


class PointLoad(BaseModel):
    """Carga pontual vertical."""

    position: float = Field(..., ge=0, description="Position in meters from the left end")
    magnitude: float = Field(..., description="Force in N, positive downward")


class Support(BaseModel):
    """Apoio no plano da viga: `pin` (fixa a posição), `roller` ou `fixed` (encastramento)."""

    position: float = Field(..., ge=0, description="Position in meters from the left end")
    type: SupportType


class SectionProperties(BaseModel):
    """Propriedades de uma secção (por exemplo IPE, HEA ou HEB) em torno do eixo de flexão."""

    area: float = Field(..., gt=0, description="Cross-section area in m^2")
    moment_of_inertia: float = Field(..., gt=0, description="Second moment of area in m^4")
    height: float = Field(..., gt=0, description="Section depth in meters (for bending stress)")
    shear_area: float | None = Field(
        default=None,
        gt=0,
        description="Effective shear area in m^2 (default: 50% of the area, a conservative guess)",
    )


class BeamRequest(BaseModel):
    """Pedido de análise de uma viga de aço: secção retangular ou propriedades explícitas."""

    length: float = Field(..., gt=0, description="Beam length in meters")
    width: float | None = Field(default=None, gt=0, description="Rectangle width in meters")
    height: float | None = Field(default=None, gt=0, description="Rectangle height in meters")
    section: SectionProperties | None = Field(
        default=None, description="Explicit section properties; replaces width and height"
    )
    include_shear_deformation: bool = Field(
        default=True, description="Timoshenko beam (True) or Euler-Bernoulli (False)"
    )
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
        """Garante secção definida, cargas e apoios dentro da viga e uma viga estável."""
        has_rectangle = self.width is not None and self.height is not None
        if has_rectangle == (self.section is not None):
            raise ValueError("Provide either width and height, or a section (not both)")
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

    @property
    def area(self) -> float:
        """Área da secção em m²."""
        if self.section is not None:
            return self.section.area
        return float(self.width or 0) * float(self.height or 0)

    @property
    def inertia(self) -> float:
        """Inércia no plano de flexão em m⁴."""
        if self.section is not None:
            return self.section.moment_of_inertia
        return float(self.width or 0) * float(self.height or 0) ** 3 / 12

    @property
    def depth(self) -> float:
        """Altura da secção em m."""
        return self.section.height if self.section is not None else float(self.height or 0)

    @property
    def shear_area(self) -> float:
        """Área de corte efetiva em m² (Cowper para o retângulo, 50 % da área se for um perfil)."""
        if self.section is not None:
            return self.section.shear_area or SECTION_SHEAR_FRACTION * self.section.area
        nu = self.poisson_ratio
        return 10 * (1 + nu) / (12 + 11 * nu) * self.area


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
