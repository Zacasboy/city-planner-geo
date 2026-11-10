"""Modelos da sugestão de materiais (T2.3)."""

from typing import Any, Literal

from pydantic import BaseModel, Field

Category = Literal["structural", "reinforcement", "masonry", "insulation", "glazing"]
Basis = Literal["per_kg", "per_m3", "per_m2"]
CarbonMetric = Literal["fossil", "total"]
SortBy = Literal["carbon", "cost"]
Exposure = Literal["general", "humid", "coastal"]


class MaterialResult(BaseModel):
    """Um material com a sua pegada de carbono A1-A3 na base pedida."""

    id: str
    name: str
    category: Category
    unit: str = Field(description="Unit of the GWP values, e.g. 'kg CO2e per m3'")
    gwp: float = Field(description="Selected carbon metric on the requested basis")
    gwp_fossil: float | None = None
    gwp_total: float | None = None
    gwp_biogenic: float | None = None
    density_kg_m3: float | None = None
    user_cost: float | None = Field(
        default=None, description="Cost supplied by the user, in the same unit as the basis"
    )
    dataset: dict[str, Any]
    notes: list[str] = Field(default_factory=list)


class SuggestResponse(BaseModel):
    """Materiais de uma categoria ordenados por carbono (ou custo)."""

    category: Category
    basis: Basis
    carbon_metric: CarbonMetric
    sort: SortBy
    results: list[MaterialResult]
    unavailable_on_basis: list[str] = Field(
        default_factory=list, description="Materials with no value on the requested basis"
    )
    notes: list[str]
    source: dict[str, Any]
