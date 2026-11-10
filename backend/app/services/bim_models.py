"""Modelos de resposta da extração de quantidades IFC (T2.4)."""

from pydantic import BaseModel


class ClassQuantities(BaseModel):
    """Quantidades somadas por classe IFC."""

    ifc_class: str
    count: int
    volume_m3: float
    area_m2: float
    length_m: float
    volume_declared_count: int
    volume_computed_count: int
    without_volume_count: int


class MaterialQuantities(BaseModel):
    """Volume somado por material (ou combinação de materiais) atribuído."""

    material: str
    composite: bool
    count: int
    volume_m3: float


class BimQuantitiesResponse(BaseModel):
    """Resultado do levantamento de quantidades de um modelo IFC."""

    schema_name: str
    project_name: str | None
    elements_total: int
    total_volume_m3: float
    by_class: list[ClassQuantities]
    by_material: list[MaterialQuantities]
    warnings: list[str]
    notes: list[str]
